"""TourAPI(한국관광공사 국문관광정보서비스) 연동 클라이언트다.

세 가지 용도로 쓴다:
- ``search_places``: STEP3 장소 검색. 서비스키가 없거나 호출이 실패해도 500 이 아니라
  EXTERNAL_API_UNAVAILABLE(503) 로 명확히 실패하도록 감싼다.
- ``fetch_nearby_places``: STEP6 대안 후보 탐색. 이쪽은 실패해도 예외를 던지지 않고 빈
  리스트를 반환해서, 후보 생성 쪽이 DB 후보 풀로 조용히 대체하게 한다.
- ``fetch_place_image``: 가이드북 장소 썸네일(detailCommon2 firstimage). 실패해도 None.

두 함수 다 lDongRegnCd/lDongSignguCd(구 단위 코드)를 응답에서 읽어 place.area_cd/signgu_cd로
쓸 값을 만드는데, 그 변환은 ``to_signgu_cd()`` 하나로 공유한다.
"""
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

import httpx
from pydantic import BaseModel

from app.clients._redact import redact_service_key
from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode

logger = logging.getLogger("yeogimalgo.tour_api")

TOUR_API_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
_TIMEOUT_SECONDS = 10.0
_UNAVAILABLE_MESSAGE = "장소 검색 서비스에 일시적으로 연결할 수 없습니다."

NEARBY_BASE_URL = "https://apis.data.go.kr/B551011/KorService2/locationBasedList2"


def to_signgu_cd(l_dong_regn_cd: str | None, l_dong_signgu_cd: str | None) -> str | None:
    """TourAPI의 lDongRegnCd(2자리)+lDongSignguCd(3자리)를 집중률 API의 signguCd(5자리)로 만든다.

    실측으로 확인된 형식: areaCd="11", signguCd="11290"(이어붙인 값)일 때만 정상 데이터가
    온다(signguCd="290" 단독은 resultCode=0000인데 0건). 이미 5자리로 들어오면(다른 경로에서
    실수로 합쳐진 값 등) 앞 2자리가 area_cd와 실제로 일치할 때만 그대로 돌려주고, 안 맞으면
    다른 지역 코드가 섞인 것이므로 None을 돌려준다.

    형식 검증을 여기서 명시적으로 한다 — 예전에는 5자리가 아니면 무조건 이어붙이기만 해서,
    예를 들어 signgu_cd가 2자리("29")로 잘려서 오면 "1129" 같은 4자리 값이 그대로
    place.area_cd/signgu_cd에 저장되고 집중률 조회 키로 쓰이는 문제가 있었다. area_cd는
    2자리 숫자, signgu_cd는 3자리 숫자(또는 접두사가 일치하는 5자리) 형식을 벗어나면
    None을 돌려준다.

    입력이 문자열이 아닐 수도 있다 — TourAPI가 lDongRegnCd를 JSON 숫자로 주면(실측된 적은
    없지만 공공데이터 API 특성상 배제 못 함) 곧바로 len()을 부르다 TypeError가 난다.
    문자열이 아니면 형식이 안 맞는 것으로 보고 None을 돌려준다(문자열로 강제 변환해서
    "맞춰 쓰지" 않는다 — 실제로 뭘 의미하는지 모르는 타입을 추측해서 저장하지 않는다).
    """
    if not l_dong_regn_cd or not l_dong_signgu_cd:
        return None
    if not isinstance(l_dong_regn_cd, str) or not isinstance(l_dong_signgu_cd, str):
        return None
    if not (len(l_dong_regn_cd) == 2 and l_dong_regn_cd.isdigit()):
        return None
    if len(l_dong_signgu_cd) == 5:
        if not l_dong_signgu_cd.isdigit():
            return None
        return l_dong_signgu_cd if l_dong_signgu_cd.startswith(l_dong_regn_cd) else None
    if not (len(l_dong_signgu_cd) == 3 and l_dong_signgu_cd.isdigit()):
        return None
    return f"{l_dong_regn_cd}{l_dong_signgu_cd}"


class TourApiPlace(BaseModel):
    """TourAPI 검색 결과 한 건을 정규화한 DTO.

    cat1/cat2/cat3 는 사람이 읽을 이름이 아니라 "A02060600" 같은 분류 코드라
    화면에 그대로 보여줄 수 없다 — 코드→이름 변환표가 생기기 전까지는 아예
    내려주지 않는다.
    """
    content_id: str
    name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    area_cd: str | None = None
    signgu_cd: str | None = None


def search_places(keyword: str, area_code: str | None = None) -> list[TourApiPlace]:
    """키워드(+지역코드) 기반 장소 검색. 실패 시 AppError(EXTERNAL_API_UNAVAILABLE) 를 던진다."""
    if not settings.TOUR_API_KEY:
        raise AppError(
            ErrorCode.EXTERNAL_API_UNAVAILABLE,
            "장소 검색 서비스 설정이 아직 준비되지 않았습니다.",
            status_code=503,
        )

    params: dict[str, Any] = {
        "serviceKey": unquote(settings.TOUR_API_KEY),
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
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("TourAPI search 호출 실패: %s", redact_service_key(str(exc)))
        # from None — exc(원본 요청 URL·서비스키 포함)가 일반 traceback 출력에 섞여 나오지
        # 않도록 억제한다(원본 exc 객체 자체를 없애는 것은 아니다). AppError 메시지 자체는
        # 고정 문구(_UNAVAILABLE_MESSAGE)라 안전하지만, 억제하지 않으면 exc가
        # traceback.format_exception()의 기본 출력에 그대로 노출될 수 있다(코드 리뷰로
        # 표현 교정, 2026-09-19).
        raise AppError(
            ErrorCode.EXTERNAL_API_UNAVAILABLE,
            _UNAVAILABLE_MESSAGE,
            status_code=503,
        ) from None

    header = payload.get("response", {}).get("header", {}) if isinstance(payload, dict) else {}
    result_code = header.get("resultCode")
    if result_code and result_code != "0000":
        logger.warning(
            "TourAPI search resultCode=%s msg=%s",
            result_code,
            header.get("resultMsg"),
        )
        raise AppError(
            ErrorCode.EXTERNAL_API_UNAVAILABLE,
            _UNAVAILABLE_MESSAGE,
            status_code=503,
        )

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
    l_dong_regn = item.get("lDongRegnCd") or None
    return TourApiPlace(
        content_id=str(item.get("contentid", "")),
        name=item.get("title", ""),
        address=item.get("addr1"),
        latitude=_to_float(item.get("mapy")),
        longitude=_to_float(item.get("mapx")),
        area_cd=l_dong_regn,
        signgu_cd=to_signgu_cd(l_dong_regn, item.get("lDongSignguCd") or None),
    )


def fetch_place_image(content_id: str) -> str | None:
    """TourAPI detailCommon2 의 firstimage. 가이드북 썸네일용이라 실패해도 None 만 돌려준다."""
    if not content_id or not settings.TOUR_API_KEY:
        return None

    params: dict[str, Any] = {
        "serviceKey": unquote(settings.TOUR_API_KEY),
        "MobileOS": "ETC",
        "MobileApp": "yeogimalgo",
        "_type": "json",
        "contentId": content_id,
    }

    try:
        response = httpx.get(
            f"{TOUR_API_BASE_URL}/detailCommon2",
            params=params,
            timeout=_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("TourAPI detailCommon2 호출 실패: %s", redact_service_key(str(exc)))
        return None

    if not isinstance(payload, dict):
        return None
    header = payload.get("response", {}).get("header", {})
    if header.get("resultCode") not in (None, "0000"):
        logger.warning(
            "TourAPI detailCommon2 resultCode=%s msg=%s",
            header.get("resultCode"),
            header.get("resultMsg"),
        )
        return None

    items = _silent_items(payload)
    if not items:
        return None
    item = items[0]
    if not isinstance(item, dict):
        return None
    url = item.get("firstimage") or item.get("firstimage2") or ""
    if not isinstance(url, str):
        return None
    url = url.strip()
    return url or None


def _silent_items(payload: dict) -> list[dict]:
    """가이드북 이미지 조회용 — 형식이 이상해도 예외 대신 빈 리스트."""
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
    """중심 좌표 기준 반경(m) 내 관광지 목록을 거리순으로 반환한다. 실패 시 빈 리스트.

    이 함수는 실패해도 예외를 던지지 않는다(설계 의도: 후보 생성 쪽이 DB 후보 풀로 조용히
    대체). 다만 items가 낯선/빈 모양일 때는 동작(빈 리스트 반환)은 그대로 두되 경고 로그는
    남겨서, 운영 중에 "진짜 0건"과 "이상한 응답이라 조용히 0건 처리된 것"을 구분할 수 있게 한다.
    """
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
        logger.warning("TourAPI 호출 실패: %s", redact_service_key(str(exc)))
        return []
    except ValueError as exc:
        # response.json()의 JSONDecodeError는 ValueError의 서브클래스다.
        logger.warning("TourAPI 응답이 올바른 JSON이 아닙니다: %s", exc)
        return []

    try:
        header = payload.get("response", {}).get("header", {})
        if header.get("resultCode") != "0000":
            logger.warning("TourAPI resultCode=%s", header.get("resultCode"))
            return []

        body = payload.get("response", {}).get("body", {})
        raw_items_container = body.get("items")
        if not isinstance(raw_items_container, dict):
            # 실측으로 확인된 모양: 결과 0건일 때 items가 dict가 아니라 빈 문자열("")로 온다.
            # 그 외 낯선 모양이 오더라도(관측된 적은 없음) 이 함수의 계약(절대 예외 안 던짐)을
            # 지키기 위해 빈 리스트로 처리하되, 조용히 넘어가지 않고 경고는 남긴다.
            if raw_items_container not in (None, ""):
                logger.warning("TourAPI 응답의 items 모양이 예상과 다름: %r", type(raw_items_container))
            return []
        raw_items = raw_items_container.get("item", [])
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        elif not isinstance(raw_items, list):
            # items.item이 리스트도 dict도 아니면(예: 숫자, None) 아래 for 루프가
            # TypeError로 죽는다 — 이 함수의 "절대 예외 안 던짐" 계약을 지키기 위해
            # 빈 리스트로 처리한다.
            logger.warning("TourAPI 응답의 items.item 모양이 예상과 다름: %r", type(raw_items))
            return []
    except (AttributeError, TypeError) as exc:
        # payload/response/body/items 중 어느 하나가 dict가 아니거나(예: payload 자체가
        # 리스트) JSON에서 명시적으로 null이면(키는 있는데 값이 None이라 .get(key, {})의
        # 기본값이 적용 안 됨) 그 다음 체이닝에서 AttributeError가 난다 — 이 함수는 절대
        # 예외를 던지지 않는 게 계약이므로 여기서 전부 빈 리스트로 흡수한다.
        logger.warning("TourAPI 응답 구조가 예상과 다릅니다: %s", exc)
        return []

    items: list[TourPlaceItem] = []
    for item in raw_items:
        if not isinstance(item, dict):
            # 리스트 안에 dict가 아닌 원소(문자열, None 등)가 섞이면 item.get()에서
            # AttributeError가 난다 — 그 원소만 건너뛰고 나머지는 계속 처리한다.
            continue
        try:
            lat = float(item.get("mapy"))
            lon = float(item.get("mapx"))
        except (TypeError, ValueError):
            continue

        l_dong_regn = item.get("lDongRegnCd") or None
        l_dong_signgu = item.get("lDongSignguCd") or None

        items.append(
            TourPlaceItem(
                content_id=str(item.get("contentid", "")),
                name=item.get("title", ""),
                latitude=lat,
                longitude=lon,
                address=item.get("addr1") or None,
                area_cd=l_dong_regn,
                signgu_cd=to_signgu_cd(l_dong_regn, l_dong_signgu),
                category_code=item.get("cat2") or None,
            )
        )
    return items
