"""TourAPI(한국관광공사 국문관광정보서비스) 연동 클라이언트다.

두 가지 용도로 쓴다:
- ``search_places``: STEP3 장소 검색. 서비스키가 없거나 호출이 실패해도 500 이 아니라
  EXTERNAL_API_UNAVAILABLE(503) 로 명확히 실패하도록 감싼다.
- ``fetch_nearby_places``: STEP6 대안 후보 탐색. 이쪽은 실패해도 예외를 던지지 않고 빈
  리스트를 반환해서, 후보 생성 쪽이 DB 후보 풀로 조용히 대체하게 한다.
"""
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode

logger = logging.getLogger("yeogimalgo.tour_api")

TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
_TIMEOUT_SECONDS = 5.0
_UNAVAILABLE_MESSAGE = "장소 검색 서비스에 일시적으로 연결할 수 없습니다."

NEARBY_BASE_URL = "https://apis.data.go.kr/B551011/KorService2/locationBasedList2"


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


@dataclass
class TourPlaceItem:
    """위치기반 관광정보 응답 item 하나."""
    content_id: str
    name: str
    latitude: float
    longitude: float
    address: str | None
    # lDongRegnCd/lDongSignguCd — 집중률 API의 area_cd/signgu_cd와 같은 코드 체계.
    area_cd: str | None
    signgu_cd: str | None
    # cat2(중분류 코드, 예: "A0206"=문화시설) — place_experience_tag 가중치 추정에 쓴다.
    category_code: str | None


def fetch_nearby_places(latitude: float, longitude: float, radius_m: int) -> list[TourPlaceItem]:
    """중심 좌표 기준 반경(m) 내 관광지 목록을 거리순으로 반환한다. 실패 시 빈 리스트."""
    if not settings.TOUR_API_KEY:
        return []

    # 집중률 API와 같은 이중 인코딩 이슈가 있을 수 있어 동일하게 방어한다.
    service_key = unquote(settings.TOUR_API_KEY)

    params: dict[str, str | int] = {
        "serviceKey": service_key,
        "numOfRows": 50,
        "pageNo": 1,
        "MobileOS": "ETC",
        "MobileApp": "여기말GO",
        "arrange": "E",  # 거리순 정렬
        "mapX": longitude,
        "mapY": latitude,
        "radius": radius_m,
        "contentTypeId": 12,  # 관광지 — 집중률 API가 커버하는 대상과 겹치도록 카페/식당 등은 제외
        "_type": "json",
    }

    try:
        response = httpx.get(NEARBY_BASE_URL, params=params, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        logger.warning("TourAPI 호출 실패: %s", exc)
        return []

    header = payload.get("response", {}).get("header", {})
    if header.get("resultCode") != "0000":
        logger.warning("TourAPI resultCode=%s", header.get("resultCode"))
        return []

    body = payload.get("response", {}).get("body", {})
    raw_items = body.get("items", {}).get("item", [])
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    items: list[TourPlaceItem] = []
    for item in raw_items:
        try:
            lat = float(item.get("mapy"))
            lon = float(item.get("mapx"))
        except (TypeError, ValueError):
            continue

        l_dong_regn = item.get("lDongRegnCd") or None
        l_dong_signgu = item.get("lDongSignguCd") or None
        signgu_cd = f"{l_dong_regn}{l_dong_signgu}" if l_dong_regn and l_dong_signgu else None

        items.append(
            TourPlaceItem(
                content_id=str(item.get("contentid", "")),
                name=item.get("title", ""),
                latitude=lat,
                longitude=lon,
                address=item.get("addr1") or None,
                area_cd=l_dong_regn,
                signgu_cd=signgu_cd,
                category_code=item.get("cat2") or None,
            )
        )
    return items
