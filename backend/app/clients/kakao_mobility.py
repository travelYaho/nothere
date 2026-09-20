"""Kakao Mobility 자동차 길찾기 클라이언트."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.core.perf import timed_external

logger = logging.getLogger(__name__)

DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"


@dataclass(frozen=True)
class RouteResult:
    distance_m: int
    duration_seconds: int
    provider: str
    is_estimated: bool
    route_source: str  # api | fallback_haversine


class KakaoMobilityClient:
    """Kakao Directions API. 키 없거나 실패 시 None (호출측에서 haversine 폴백)."""

    def __init__(self, api_key: str | None = None, timeout: float = 15.0) -> None:
        self.api_key = (api_key if api_key is not None else settings.KAKAO_REST_API_KEY).strip()
        self.timeout = timeout

    def directions(
        self,
        origin_lng: float,
        origin_lat: float,
        dest_lng: float,
        dest_lat: float,
    ) -> RouteResult | None:
        if not self.api_key:
            logger.warning("KAKAO_REST_API_KEY 없음 — Directions 호출 생략")
            return None

        headers = {
            "Authorization": f"KakaoAK {self.api_key}",
            "Content-Type": "application/json",
        }
        params = {
            "origin": f"{origin_lng},{origin_lat}",
            "destination": f"{dest_lng},{dest_lat}",
        }
        try:
            with timed_external("kakao_directions"):
                response = httpx.get(
                    DIRECTIONS_URL,
                    headers=headers,
                    params=params,
                    timeout=self.timeout,
                )
        except httpx.RequestError as exc:
            logger.warning("Kakao Directions 요청 실패: %s", exc)
            return None

        if response.status_code != 200:
            logger.warning("Kakao Directions HTTP %s: %s", response.status_code, response.text[:200])
            return None

        data = response.json()
        routes = data.get("routes") or []
        if not routes:
            return None
        route = routes[0]
        result_code = route.get("result_code")
        if result_code not in (0, "0", None) and not route.get("summary"):
            return None
        summary = route.get("summary") or {}
        distance = summary.get("distance")
        duration = summary.get("duration")
        if distance is None or duration is None:
            return None
        return RouteResult(
            distance_m=int(distance),
            duration_seconds=int(duration),
            provider="kakao_mobility",
            is_estimated=False,
            route_source="api",
        )


def raise_if_kakao_hard_required() -> None:
    """필수 경로 API가 완전히 불가할 때 사용 (현재는 soft fail)."""
    raise AppError(
        ErrorCode.EXTERNAL_API_UNAVAILABLE,
        "경로 API를 사용할 수 없습니다.",
        status_code=503,
    )
