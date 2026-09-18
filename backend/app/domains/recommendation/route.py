"""경로 거리·시간 계산 및 route_cache."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.kakao_mobility import KakaoMobilityClient, RouteResult
from app.core.config import settings
from app.db.models.route_cache import RouteCache
from app.utils.geo import get_place_coords

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
            return RouteResult(
                distance_m=cached.distance_m,
                duration_seconds=cached.duration_seconds,
                provider=cached.provider,
                is_estimated=cached.is_estimated,
                route_source="fallback_haversine" if cached.is_estimated else "api",
            )

        origin = get_place_coords(self.db, origin_place_id)
        dest = get_place_coords(self.db, dest_place_id)
        if origin is None or dest is None:
            return None

        o_lat, o_lng = origin
        d_lat, d_lng = dest

        result: RouteResult | None = None
        # Kakao Directions 는 자동차 기준. walk/transit 도 거리 참고용으로 호출 후 필요 시 보정
        if transport_mode in ("car", "public_transit", "walk"):
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
        elif transport_mode == "walk" and not result.is_estimated:
            # 자동차 경로를 받았더라도 도보면 직선 기반 재추정
            distance = int(haversine_m(o_lat, o_lng, d_lat, d_lng) * 1.3)
            result = RouteResult(
                distance_m=distance,
                duration_seconds=estimate_duration_seconds(distance, "walk"),
                provider="haversine",
                is_estimated=True,
                route_source="fallback_haversine",
            )

        self._put_cache(origin_place_id, dest_place_id, transport_mode, result)
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
