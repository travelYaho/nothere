"""TourAPI(한국관광공사 국문관광정보서비스) 장소검색 연동 클라이언트다.

서비스키가 없거나 호출이 실패해도 500 이 아니라 EXTERNAL_API_UNAVAILABLE(503)
로 명확히 실패하도록 감싼다. 지금은 TOUR_API_KEY 가 미발급 상태라, 인터페이스만
완성해 두고 키가 발급되면 .env 값만 채우면 바로 붙도록 분리했다.
"""
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode

TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
_TIMEOUT_SECONDS = 5.0
_UNAVAILABLE_MESSAGE = "장소 검색 서비스에 일시적으로 연결할 수 없습니다."


class TourApiPlace(BaseModel):
    """TourAPI 검색 결과 한 건을 정규화한 DTO."""
    content_id: str
    name: str
    category: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


def search_places(keyword: str, area_code: str | None = None) -> list[TourApiPlace]:
    """키워드(+지역코드) 기반 장소 검색. 실패 시 AppError(EXTERNAL_API_UNAVAILABLE) 를 던진다."""
    if not settings.TOUR_API_KEY:
        raise AppError(
            ErrorCode.EXTERNAL_API_UNAVAILABLE,
            "장소 검색 서비스 설정이 아직 준비되지 않았습니다.",
            status_code=503,
        )

    params: dict[str, Any] = {
        "serviceKey": settings.TOUR_API_KEY,
        "MobileOS": "ETC",
        "MobileApp": "yeogimalgo",
        "_type": "json",
        "keyword": keyword,
        "numOfRows": 20,
    }
    if area_code:
        params["areaCode"] = area_code

    try:
        response = httpx.get(
            f"{TOUR_API_BASE_URL}/searchKeyword2",
            params=params,
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AppError(
            ErrorCode.EXTERNAL_API_UNAVAILABLE,
            _UNAVAILABLE_MESSAGE,
            status_code=503,
        ) from exc

    return [_to_place(item) for item in _extract_items(payload)]


def _extract_items(payload: dict) -> list[dict]:
    """TourAPI 표준 응답 껍데기(response.body.items.item)를 벗겨 리스트로 만든다."""
    try:
        body = payload["response"]["body"]
        total_count = body.get("totalCount", 0)
        if not total_count:
            return []
        items = body["items"]["item"]
    except (KeyError, TypeError) as exc:
        raise AppError(
            ErrorCode.EXTERNAL_API_UNAVAILABLE,
            "장소 검색 서비스 응답 형식이 올바르지 않습니다.",
            status_code=503,
        ) from exc

    # 결과가 1건이면 TourAPI 가 item 을 배열이 아니라 객체 하나로 내려준다.
    if isinstance(items, dict):
        items = [items]
    return items


def _to_place(item: dict) -> TourApiPlace:
    return TourApiPlace(
        content_id=str(item.get("contentid", "")),
        name=item.get("title", ""),
        category=item.get("cat3") or item.get("cat1"),
        address=item.get("addr1"),
        latitude=_to_float(item.get("mapy")),
        longitude=_to_float(item.get("mapx")),
    )


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
