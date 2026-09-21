"""경로 거리·시간 계산 및 route_cache."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.kakao_mobility import KakaoMobilityClient, RouteResult
from app.core.config import settings
from app.db.models.route_cache import RouteCache
from app.utils.geo import get_place_coords, get_place_coords_map

# 도보 ~4.5km/h, 대중교통·자동차 추정치용 평균 속도(km/h)
_SPEED_KMH = {
    "walk": 4.5,
    "public_transit": 25.0,
    "car": 30.0,
}


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return int(2 * r * math.asin(math.sqrt(a)))


def estimate_duration_seconds(distance_m: int, transport_mode: str) -> int:
    speed = _SPEED_KMH.get(transport_mode, _SPEED_KMH["car"])
    hours = (distance_m / 1000.0) / speed
    return max(60, int(hours * 3600))


class RouteService:
    PROVIDER = "kakao_mobility"

    def __init__(self, db: Session, client: KakaoMobilityClient | None = None) -> None:
        self.db = db
        self.client = client or KakaoMobilityClient()

    def get_leg(
        self,
        origin_place_id: UUID,
        dest_place_id: UUID,
        transport_mode: str,
    ) -> RouteResult | None:
        cached = self._get_cache(origin_place_id, dest_place_id, transport_mode)
        if cached is not None:
            return self._from_cache_row(cached)

        origin = get_place_coords(self.db, origin_place_id)
        dest = get_place_coords(self.db, dest_place_id)
        if origin is None or dest is None:
            return None

        result = self._resolve_leg(origin, dest, transport_mode)
        self._put_cache(origin_place_id, dest_place_id, transport_mode, result)
        return result

    def get_legs(
        self,
        pairs: list[tuple[UUID, UUID]],
        transport_mode: str,
    ) -> dict[tuple[UUID, UUID], RouteResult]:
        """여러 구간을 한 번에 구한다(가이드북처럼 정류장이 여러 개일 때용).

        get_leg()를 구간 수만큼(정류장 N개면 N-1번) 반복하면 캐시 조회 1회 + 캐시
        미스 시 좌표 조회 2회가 구간마다 DB 왕복을 냈다 — 캐시 조회를 IN 절 하나로
        모으고, 캐시 미스 구간의 좌표도 한 번에 가져온다. 캐시가 이미 있는(=대부분의
        재방문) 경우 DB 왕복이 구간 수와 무관하게 1회로 끝난다. 다만 캐시 미스로
        실제 Kakao Directions 호출이 필요한 구간은 외부 API라 왕복을 묶을 수 없어
        get_leg()와 동일하게 구간별로 순차 호출한다.
        """
        unique_pairs = list(dict.fromkeys(pairs))
        if not unique_pairs:
            return {}

        cached_rows = self._get_cache_many(unique_pairs, transport_mode)
        results: dict[tuple[UUID, UUID], RouteResult] = {
            pair: self._from_cache_row(row) for pair, row in cached_rows.items()
        }

        missing = [pair for pair in unique_pairs if pair not in results]
        if missing:
            place_ids = list({place_id for pair in missing for place_id in pair})
            coords = get_place_coords_map(self.db, place_ids)
            for origin_id, dest_id in missing:
                origin = coords.get(str(origin_id))
                dest = coords.get(str(dest_id))
                if origin is None or dest is None:
                    continue
                result = self._resolve_leg(origin, dest, transport_mode)
                self._put_cache(origin_id, dest_id, transport_mode, result)
                results[(origin_id, dest_id)] = result

        return results

    def _resolve_leg(
        self,
        origin: tuple[float, float],
        dest: tuple[float, float],
        transport_mode: str,
    ) -> RouteResult:
        o_lat, o_lng = origin
        d_lat, d_lng = dest

        result: RouteResult | None = None
        # Kakao Directions 는 자동차 기준. transit 은 거리 참고용으로 호출하고, walk 는 어차피
        # 아래에서 직선거리로 재추정하므로 외부 호출(구간당 수백 ms) 없이 바로 fallback 한다.
        if transport_mode in ("car", "public_transit"):
            result = self.client.directions(o_lng, o_lat, d_lng, d_lat)

        if result is None:
            distance = haversine_m(o_lat, o_lng, d_lat, d_lng)
            # 도보는 직선×1.3, 그 외 ×1.2 보정
            factor = 1.3 if transport_mode == "walk" else 1.2
            distance = int(distance * factor)
            duration = estimate_duration_seconds(distance, transport_mode)
            result = RouteResult(
                distance_m=distance,
                duration_seconds=duration,
                provider="haversine",
                is_estimated=True,
                route_source="fallback_haversine",
            )

        return result

    def _from_cache_row(self, cached: RouteCache) -> RouteResult:
        return RouteResult(
            distance_m=cached.distance_m,
            duration_seconds=cached.duration_seconds,
            provider=cached.provider,
            is_estimated=cached.is_estimated,
            route_source="fallback_haversine" if cached.is_estimated else "api",
        )

    def _get_cache_many(
        self,
        pairs: list[tuple[UUID, UUID]],
        transport_mode: str,
    ) -> dict[tuple[UUID, UUID], RouteCache]:
        now = datetime.now(timezone.utc)
        rows = (
            self.db.query(RouteCache)
            .filter(
                tuple_(RouteCache.origin_place_id, RouteCache.destination_place_id).in_(pairs),
                RouteCache.transport_mode == transport_mode,
                RouteCache.provider.in_((self.PROVIDER, "haversine")),
                RouteCache.expires_at > now,
            )
            .order_by(
                RouteCache.origin_place_id,
                RouteCache.destination_place_id,
                RouteCache.fetched_at.desc(),
            )
            .all()
        )
        result: dict[tuple[UUID, UUID], RouteCache] = {}
        for row in rows:
            key = (row.origin_place_id, row.destination_place_id)
            result.setdefault(key, row)  # 그룹 내 fetched_at desc 정렬이라 첫 값이 최신
        return result

    def _get_cache(
        self,
        origin_place_id: UUID,
        dest_place_id: UUID,
        transport_mode: str,
    ) -> RouteCache | None:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(RouteCache)
            .filter(
                RouteCache.origin_place_id == origin_place_id,
                RouteCache.destination_place_id == dest_place_id,
                RouteCache.transport_mode == transport_mode,
                RouteCache.provider.in_((self.PROVIDER, "haversine")),
                RouteCache.expires_at > now,
            )
            .order_by(RouteCache.fetched_at.desc())
            .first()
        )

    def _put_cache(
        self,
        origin_place_id: UUID,
        dest_place_id: UUID,
        transport_mode: str,
        result: RouteResult,
    ) -> None:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=settings.ROUTE_CACHE_TTL_HOURS)
        insert_stmt = pg_insert(RouteCache).values(
            origin_place_id=origin_place_id,
            destination_place_id=dest_place_id,
            transport_mode=transport_mode,
            distance_m=result.distance_m,
            duration_seconds=result.duration_seconds,
            provider=result.provider,
            is_estimated=result.is_estimated,
            fetched_at=now,
            expires_at=expires,
        )
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                "origin_place_id",
                "destination_place_id",
                "transport_mode",
                "provider",
            ],
            set_={
                "distance_m": insert_stmt.excluded.distance_m,
                "duration_seconds": insert_stmt.excluded.duration_seconds,
                "is_estimated": insert_stmt.excluded.is_estimated,
                "fetched_at": insert_stmt.excluded.fetched_at,
                "expires_at": insert_stmt.excluded.expires_at,
            },
        )
        self.db.execute(stmt)
        self.db.flush()
