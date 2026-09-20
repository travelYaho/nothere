"""한국관광공사 관광사진 정보_GW (PhotoGalleryService1) 클라이언트다.

가이드북 표지(시·구 랜덤)와, TourAPI firstimage 가 없는 장소의 키워드 검색 폴백에 쓴다.
키가 없거나 호출이 실패해도 가이드북 조회 자체를 막지 않도록 예외를 던지지 않는다.

PhotoGalleryService2 는 공공데이터포털에서 폐기되어(NO_OPENAPI_SERVICE_ERROR)
gallerySearchList1 을 쓴다. 이 API 는 KorService2 와 활용신청/키가 다르다.
"""
import logging
import random
import re
from typing import Any
from urllib.parse import unquote

import httpx

from app.clients._redact import redact_service_key
from app.core.config import settings

logger = logging.getLogger("yeogimalgo.photo_gallery")

PHOTO_GALLERY_BASE_URL = "https://apis.data.go.kr/B551011/PhotoGalleryService1"
_TIMEOUT_SECONDS = 10.0
_PAREN_SUFFIX = re.compile(r"\([^)]*\)")


def _gallery_key() -> str:
    return unquote(settings.PHOTO_GALLERY_API_KEY or settings.TOUR_API_KEY or "")


def search_image_urls(keyword: str, *, num_of_rows: int = 20) -> list[str]:
    """키워드로 관광사진 URL 목록을 가져온다. 실패/없음이면 빈 리스트."""
    cleaned = keyword.strip() if keyword else ""
    service_key = _gallery_key()
    if not cleaned or not service_key:
        return []

    params: dict[str, Any] = {
        "serviceKey": service_key,
        "MobileOS": "ETC",
        "MobileApp": "yeogimalgo",
        "_type": "json",
        "keyword": cleaned,
        "numOfRows": num_of_rows,
        "pageNo": 1,
    }

    try:
        response = httpx.get(
            f"{PHOTO_GALLERY_BASE_URL}/gallerySearchList1",
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
    if "OpenAPI_ServiceResponse" in payload:
        header = payload.get("OpenAPI_ServiceResponse", {}).get("cmmMsgHeader", {})
        logger.warning(
            "PhotoGallery gateway err=%s msg=%s",
            header.get("errMsg"),
            header.get("returnAuthMsg"),
        )
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
        url = _prefer_https(raw.strip())
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def pick_cover_image(city: str | None, district: str | None) -> str | None:
    """일정 장소 사진이 없을 때 쓰는 표지 폴백. 다수 구 → 시 순이다."""
    city_name = city.strip() if city else ""
    district_name = district.strip() if district else ""
    keywords: list[str] = []
    if district_name:
        if city_name:
            keywords.append(f"{city_name} {district_name}")
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
    for keyword in _place_keywords(place_name):
        urls = search_image_urls(keyword, num_of_rows=1)
        if urls:
            return urls[0]
    return None


def _place_keywords(place_name: str) -> list[str]:
    cleaned = place_name.strip() if place_name else ""
    if not cleaned:
        return []
    keywords = [cleaned]
    stripped = _PAREN_SUFFIX.sub("", cleaned).strip()
    if stripped and stripped not in keywords:
        keywords.append(stripped)
    return keywords


def _prefer_https(url: str) -> str:
    if url.startswith("http://tong.visitkorea.or.kr"):
        return "https://" + url[len("http://") :]
    return url


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
