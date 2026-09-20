"""한국관광공사 관광사진 정보_GW (PhotoGalleryService2) 클라이언트다.

가이드북 표지(시·구 랜덤)와, TourAPI firstimage 가 없는 장소의 키워드 검색 폴백에 쓴다.
키가 없거나 호출이 실패해도 가이드북 조회 자체를 막지 않도록 예외를 던지지 않는다.
"""
import logging
import random
from typing import Any
from urllib.parse import unquote

import httpx

from app.clients._redact import redact_service_key
from app.core.config import settings

logger = logging.getLogger("yeogimalgo.photo_gallery")

PHOTO_GALLERY_BASE_URL = "https://apis.data.go.kr/B551011/PhotoGalleryService2"
_TIMEOUT_SECONDS = 10.0


def search_image_urls(keyword: str, *, num_of_rows: int = 20) -> list[str]:
    """키워드로 관광사진 URL 목록을 가져온다. 실패/없음이면 빈 리스트."""
    cleaned = keyword.strip() if keyword else ""
    if not cleaned or not settings.TOUR_API_KEY:
        return []

    params: dict[str, Any] = {
        "serviceKey": unquote(settings.TOUR_API_KEY),
        "MobileOS": "ETC",
        "MobileApp": "yeogimalgo",
        "_type": "json",
        "keyword": cleaned,
        "numOfRows": num_of_rows,
        "pageNo": 1,
    }

    try:
        response = httpx.get(
            f"{PHOTO_GALLERY_BASE_URL}/gallerySearchList2",
            params=params,
            timeout=_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("PhotoGallery 호출 실패: %s", redact_service_key(str(exc)))
        return []

    if not isinstance(payload, dict):
        return []
    header = payload.get("response", {}).get("header", {}) if isinstance(payload.get("response"), dict) else {}
    result_code = header.get("resultCode")
    if result_code and result_code != "0000":
        logger.warning(
            "PhotoGallery resultCode=%s msg=%s",
            result_code,
            header.get("resultMsg"),
        )
        return []

    urls: list[str] = []
    seen: set[str] = set()
    for item in _silent_items(payload):
        raw = item.get("galWebImageUrl") or item.get("galWebOriginUrl") or ""
        if not isinstance(raw, str):
            continue
        url = raw.strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def pick_cover_image(city: str | None, district: str | None) -> str | None:
    """시·구에 맞는 관광사진 중 랜덤 1장. 구가 없으면 시만으로 재시도한다."""
    city_name = city.strip() if city else ""
    district_name = district.strip() if district else ""
    keywords: list[str] = []
    if city_name and district_name:
        keywords.append(f"{city_name} {district_name}")
    if district_name:
        keywords.append(district_name)
    if city_name:
        keywords.append(city_name)

    for keyword in keywords:
        urls = search_image_urls(keyword)
        if urls:
            return random.choice(urls)
    return None


def first_image_for_place(place_name: str) -> str | None:
    """장소명 키워드 검색 첫 장. 매칭이 애매하면 없는 것과 같아서 1건만 본다."""
    urls = search_image_urls(place_name, num_of_rows=1)
    return urls[0] if urls else None


def _silent_items(payload: dict) -> list[dict]:
    try:
        body = payload["response"]["body"]
        total_count = body.get("totalCount", 0)
        if not total_count:
            return []
        items = body["items"]["item"]
    except (KeyError, TypeError):
        return []
    if isinstance(items, dict):
        return [items]
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []
