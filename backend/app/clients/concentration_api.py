"""집중률 API(TatsCnctrRateService) 호출 래퍼.

CONCENTRATION_API_KEY가 비어 있으면(아직 발급/공유 전) 호출 자체를 시도하지 않고
ConcentrationApiError를 던져 analysis 서비스가 analysis_status="failed"로 안전하게 처리한다.
"""
import logging
from dataclasses import dataclass
from urllib.parse import unquote

import httpx

from app.core.config import settings

logger = logging.getLogger("yeogimalgo.concentration_api")

BASE_URL = "https://apis.data.go.kr/B551011/TatsCnctrRateService/tatsCnctrRatedList"
_PAGE_SIZE = 100
_MAX_PAGES = 100  # 안전장치 — totalCount가 비정상적으로 크게 와도 무한 루프에 안 빠지게


class ConcentrationApiError(Exception):
    """호출/응답 처리 중 발생한 오류. resultCode(있으면)와 재시도 가능 여부를 함께 담는다."""

    def __init__(self, message: str, result_code: str | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.result_code = result_code
        self.retryable = retryable


@dataclass
class ConcentrationItem:
    """응답 item 하나. cnctrRate가 실제 집중률 값이다."""
    tourist_name: str
    area_cd: str
    signgu_cd: str
    base_ymd: str
    raw_value: float | None


def _to_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _fetch_page(
    area_cd: str,
    signgu_cd: str,
    service_key: str,
    page_no: int,
    tourist_name: str | None,
) -> tuple[list[ConcentrationItem], int]:
    """한 페이지를 호출해 (item 리스트, totalCount)를 반환한다."""
    params: dict[str, str | int] = {
        "serviceKey": service_key,
        "areaCd": area_cd,
        "signguCd": signgu_cd,
        "MobileOS": "ETC",
        "MobileApp": "여기말GO",
        "numOfRows": _PAGE_SIZE,
        "pageNo": page_no,
        "_type": "json",
    }
    if tourist_name:
        params["tAtsNm"] = tourist_name

    try:
        response = httpx.get(BASE_URL, params=params, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise ConcentrationApiError(
            f"집중률 API 호출 실패: {exc}", result_code=None, retryable=True
        ) from exc

    header = payload.get("response", {}).get("header", {})
    body = payload.get("response", {}).get("body", {})
    result_code = header.get("resultCode")

    if result_code == "0000":
        pass
    elif result_code == "03":
        # 데이터없음 — 호출측이 no_forecast_data(unavailable)로 처리하도록 빈 리스트 반환
        return [], 0
    elif result_code == "22":
        raise ConcentrationApiError("요청 제한 횟수 초과", result_code=result_code, retryable=True)
    elif result_code == "30":
        logger.error("집중률 API 미등록 서비스키 (resultCode=30)")
        raise ConcentrationApiError("미등록 서비스키", result_code=result_code, retryable=False)
    elif result_code == "05":
        raise ConcentrationApiError("서비스 연결실패", result_code=result_code, retryable=True)
    else:
        logger.error("집중률 API 알 수 없는 resultCode=%s", result_code)
        raise ConcentrationApiError(
            f"알 수 없는 응답 코드: {result_code}", result_code=result_code, retryable=False
        )

    raw_items = body.get("items", {}).get("item", [])
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    items = [
        ConcentrationItem(
            tourist_name=item.get("tAtsNm", ""),
            area_cd=item.get("areaCd", area_cd),
            signgu_cd=item.get("signguCd", signgu_cd),
            base_ymd=item.get("baseYmd", ""),
            raw_value=_to_float(item.get("cnctrRate")),
        )
        for item in raw_items
    ]
    total_count = int(body.get("totalCount") or 0)
    return items, total_count


def fetch_concentration(
    area_cd: str,
    signgu_cd: str,
    tourist_name: str | None = None,
) -> list[ConcentrationItem]:
    """지역 단위로 집중률 API를 호출해 관광지별 원본 항목 리스트를 전체 페이지에 걸쳐 반환한다.

    baseYmd는 요청 파라미터가 아니다 — 한 번 호출하면 향후 30일치가 자동 포함된다.
    지역 전체는 totalCount가 수천 건(관광지 수 x 30일)에 달해 한 페이지(100건)로는
    다 못 받으므로, totalCount를 다 채울 때까지 페이지를 순회한다.
    """
    if not settings.CONCENTRATION_API_KEY:
        raise ConcentrationApiError(
            "CONCENTRATION_API_KEY가 설정되어 있지 않습니다.", result_code=None, retryable=False
        )

    # 공공데이터포털 "Encoding" 키(이미 %-인코딩됨)를 그대로 넣는 경우가 흔한데,
    # httpx가 params를 다시 인코딩하면서 %2B 등이 %252B로 이중 인코딩되어 403이 난다.
    # unquote()는 인코딩 안 된 키에는 영향이 없으므로 항상 걸어도 안전하다.
    service_key = unquote(settings.CONCENTRATION_API_KEY)

    all_items: list[ConcentrationItem] = []
    page_no = 1
    while page_no <= _MAX_PAGES:
        items, total_count = _fetch_page(area_cd, signgu_cd, service_key, page_no, tourist_name)
        all_items.extend(items)
        if not items or page_no * _PAGE_SIZE >= total_count:
            break
        page_no += 1

    return all_items
