"""Kakao 로컬 API(주소 검색) 연동 클라이언트다.

장소를 직접 추가할 때 사용자가 입력한 주소 문자열을 위경도로 지오코딩하는
용도로만 쓴다. 서비스키가 없거나 호출이 실패해도 500 이 아니라
EXTERNAL_API_UNAVAILABLE(503) 로 명확히 실패하도록 감싼다.
"""
import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode

KAKAO_API_BASE_URL = "https://dapi.kakao.com/v2/local/search/address.json"
_TIMEOUT_SECONDS = 5.0
_UNAVAILABLE_MESSAGE = "주소 검색 서비스에 일시적으로 연결할 수 없습니다."


class GeocodedAddress(BaseModel):
    """지오코딩 결과 좌표."""
    latitude: float
    longitude: float


def geocode_address(address: str) -> GeocodedAddress | None:
    """주소 문자열을 위경도로 변환한다. 검색 결과가 0건이면 None 을 반환한다
    (주소 자체가 이상한 것과 서비스 장애를 구분하기 위해 예외로 던지지 않는다).
    """
    if not settings.KAKAO_REST_API_KEY:
        raise AppError(
            ErrorCode.EXTERNAL_API_UNAVAILABLE,
            "주소 검색 서비스 설정이 아직 준비되지 않았습니다.",
            status_code=503,
        )

    try:
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

    documents = payload.get("documents") or []
    if not documents:
        return None

    first = documents[0]
    try:
        return GeocodedAddress(latitude=float(first["y"]), longitude=float(first["x"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(
            ErrorCode.EXTERNAL_API_UNAVAILABLE,
            "주소 검색 서비스 응답 형식이 올바르지 않습니다.",
            status_code=503,
        ) from exc
