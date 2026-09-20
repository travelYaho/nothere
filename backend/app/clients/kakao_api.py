"""Kakao 로컬 API(주소 검색) 연동 클라이언트다.

장소를 직접 추가할 때 사용자가 입력한 주소 문자열을 위경도로 지오코딩하는
용도로만 쓴다. 서비스키가 없거나 호출이 실패해도 500 이 아니라
EXTERNAL_API_UNAVAILABLE(503) 로 명확히 실패하도록 감싼다.
"""
import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.core.perf import timed_external

KAKAO_API_BASE_URL = "https://dapi.kakao.com/v2/local/search/address.json"
_TIMEOUT_SECONDS = 5.0
_UNAVAILABLE_MESSAGE = "주소 검색 서비스에 일시적으로 연결할 수 없습니다."
_MALFORMED_MESSAGE = "주소 검색 서비스 응답 형식이 올바르지 않습니다."
_AMBIGUOUS_MESSAGE = "주소가 여러 곳으로 검색돼요. 더 정확한 주소를 입력해 주세요."
_MISMATCH_MESSAGE = "입력한 주소와 검색된 주소가 달라요. 주소 검색에서 선택한 주소를 그대로 입력해 주세요."

# REGION(행정구역 중심)·ROAD(도로명만) 결과는 건물 단위 좌표가 아니라서 쓰지 않는다.
_PRECISE_ADDRESS_TYPES = frozenset({"ROAD_ADDR", "REGION_ADDR"})


class GeocodedAddress(BaseModel):
    """지오코딩 결과 좌표."""
    latitude: float
    longitude: float


def _malformed() -> AppError:
    return AppError(ErrorCode.EXTERNAL_API_UNAVAILABLE, _MALFORMED_MESSAGE, status_code=503)


def _normalize(text: str) -> str:
    return "".join(text.split())


def _matches_request(address: str, address_name: str) -> bool:
    if _normalize(address) == _normalize(address_name):
        return True
    # baseAddress 없이 상세주소(층·호수 등)까지 붙어 온 입력 — 결과 주소 바로 뒤가 공백일 때만
    # 상세주소로 본다("세종대로 110"의 "1103"처럼 번지가 이어진 경우는 다른 주소다).
    return " ".join(address.split()).startswith(" ".join(address_name.split()) + " ")


def _parse_point(document: object) -> GeocodedAddress:
    if not isinstance(document, dict):
        raise _malformed()
    try:
        # Kakao 응답의 y가 위도, x가 경도다.
        latitude = float(document["y"])
        longitude = float(document["x"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _malformed() from exc
    # NaN/inf도 이 범위 비교에서 걸러진다.
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        raise _malformed()
    return GeocodedAddress(latitude=latitude, longitude=longitude)


def geocode_address(address: str) -> GeocodedAddress | None:
    """주소 문자열을 위경도로 변환한다. 쓸 수 있는 검색 결과가 없으면 None 을 반환한다
    (주소 자체가 이상한 것과 서비스 장애를 구분하기 위해 예외로 던지지 않는다).
    요청 주소와 (공백을 무시하고) 일치하는 결과가 하나일 때만 쓰고(뒤에 공백으로 이어진 상세주소는 허용), 일치하는 결과가 없거나
    여러 개면 임의로 고르지 않고 ADDRESS_NOT_FOUND(400)로 거절한다.
    """
    if not settings.KAKAO_REST_API_KEY:
        raise AppError(
            ErrorCode.EXTERNAL_API_UNAVAILABLE,
            "주소 검색 서비스 설정이 아직 준비되지 않았습니다.",
            status_code=503,
        )

    try:
        with timed_external("kakao_geocode"):
            response = httpx.get(
                KAKAO_API_BASE_URL,
                params={"query": address},
                headers={"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"},
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

    if not isinstance(payload, dict):
        raise _malformed()
    documents = payload.get("documents")
    if documents is None:
        documents = []
    if not isinstance(documents, list):
        raise _malformed()

    if not all(isinstance(doc, dict) for doc in documents):
        raise _malformed()
    precise = [doc for doc in documents if doc.get("address_type") in _PRECISE_ADDRESS_TYPES]
    if not precise:
        return None

    # 존재하지 않는 번지를 넣으면 카카오가 비슷한 다른 주소(예: "세종대로 2" → "세종대로 지하 2")를
    # 대신 돌려주는데, 그게 하나뿐이어도 다른 위치다 — 요청 주소와 정확히 같은 결과가 하나일
    # 때만 좌표를 쓴다.
    exact = [
        doc
        for doc in precise
        if isinstance(doc.get("address_name"), str) and _matches_request(address, doc["address_name"])
    ]
    if len(exact) != 1:
        message = _AMBIGUOUS_MESSAGE if len(precise) > 1 else _MISMATCH_MESSAGE
        raise AppError(ErrorCode.ADDRESS_NOT_FOUND, message, status_code=400)
    return _parse_point(exact[0])
