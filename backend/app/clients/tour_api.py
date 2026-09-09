"""TourAPI(한국관광공사_국문 관광정보 서비스_GW) 위치기반 관광정보조회 래퍼.

STEP6 대안 후보 탐색에 쓴다. TOUR_API_KEY가 비어 있거나 호출이 실패하면 예외를 던지지
않고 빈 리스트를 반환해서, 후보 생성 쪽이 DB 후보 풀로 조용히 대체하게 한다.
"""
import logging
from dataclasses import dataclass
from urllib.parse import unquote

import httpx

from app.core.config import settings

logger = logging.getLogger("yeogimalgo.tour_api")

BASE_URL = "https://apis.data.go.kr/B551011/KorService2/locationBasedList2"


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
        response = httpx.get(BASE_URL, params=params, timeout=10.0)
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
