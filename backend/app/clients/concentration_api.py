"""집중률 API(TatsCnctrRateService) 호출 래퍼.

CONCENTRATION_API_KEY가 비어 있으면(아직 발급/공유 전) 호출 자체를 시도하지 않고
ConcentrationApiError를 던져 analysis 서비스가 analysis_status="failed"로 안전하게 처리한다.
"""
import logging
import math
from dataclasses import dataclass
from urllib.parse import unquote

import httpx

from app.core.config import settings

logger = logging.getLogger("yeogimalgo.concentration_api")

BASE_URL = "https://apis.data.go.kr/B551011/TatsCnctrRateService/tatsCnctrRatedList"
_PAGE_SIZE = 100
_HARD_MAX_PAGES = 100  # 정상 종료 조건이 아니라, 응답이 비정상적으로 큰 경우를 막는 안전 상한
_PAGE_RETRY_LIMIT = 2  # 더 받을 데이터가 남았는데 페이지가 비어 오면 같은 페이지를 재시도하는 횟수


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
    """한 페이지를 호출해 (item 리스트, totalCount)를 반환한다.

    이 함수 자체는 빈 페이지가 나와도 절대 예외를 던지지 않는다 — 재시도할지는 호출자
    (fetch_concentration)가 total_count와 지금까지 모은 개수를 보고 판단한다. items가
    dict도 아니고, 실측으로 확인된 "빈 문자열" 모양도 아닌 그 외의 낯선 구조일 때만
    이 함수가 직접 ConcentrationApiError를 던진다 — 재시도로 해결될 문제가 아니기 때문이다.
    """
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
    except ValueError as exc:
        # response.json()의 JSONDecodeError는 ValueError의 서브클래스다.
        raise ConcentrationApiError(
            f"집중률 API 응답이 올바른 JSON이 아닙니다: {exc}", result_code=None, retryable=True
        ) from exc

    try:
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

        raw_items_container = body.get("items")
        if isinstance(raw_items_container, dict):
            raw_items = raw_items_container.get("item", [])
        elif raw_items_container in (None, ""):
            # 실측으로 확인된 모양: 결과 0건일 때 items가 dict가 아니라 빈 문자열("")로 온다.
            raw_items = []
        else:
            raise ConcentrationApiError(
                f"알 수 없는 items 응답 형식: {type(raw_items_container)}",
                result_code=result_code,
                retryable=False,
            )
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
    except ConcentrationApiError:
        raise  # 위에서 의도적으로 던진 건 그대로 통과시킨다.
    except (AttributeError, TypeError, ValueError, KeyError) as exc:
        # payload가 dict가 아니거나(AttributeError), items.item이 null이라 순회 불가하거나
        # (TypeError), 리스트 안에 dict가 아닌 원소가 섞였거나(AttributeError), totalCount가
        # 숫자로 변환 안 되는 등(ValueError) — 응답 구조 자체가 예상과 다른 경우를 전부 잡는다.
        # 이게 없으면 이 함수 하나의 실패가 analysis 서비스의 장소별 failed 처리 대신
        # run_analysis() 전체를 죽이는 500으로 새어나간다.
        raise ConcentrationApiError(
            f"집중률 API 응답 구조가 예상과 다릅니다: {exc}", result_code=None, retryable=False
        ) from exc

    if total_count < 0:
        # int() 변환 자체는 성공하지만 의미가 없는 값이라 별도로 검증한다.
        raise ConcentrationApiError(
            f"집중률 API totalCount가 음수입니다: {total_count}", result_code=result_code, retryable=False
        )

    return items, total_count


def _fetch_page_with_retry(
    area_cd: str,
    signgu_cd: str,
    service_key: str,
    page_no: int,
    tourist_name: str | None,
) -> tuple[list[ConcentrationItem], int]:
    """빈 페이지가 나왔는데 total_count 상 데이터가 더 있어야 하면 같은 페이지를 재시도한다."""
    items, total_count = _fetch_page(area_cd, signgu_cd, service_key, page_no, tourist_name)
    if items or total_count == 0:
        return items, total_count
    for _ in range(_PAGE_RETRY_LIMIT):
        items, total_count = _fetch_page(area_cd, signgu_cd, service_key, page_no, tourist_name)
        if items:
            break
    return items, total_count


def fetch_concentration(
    area_cd: str,
    signgu_cd: str,
    tourist_name: str | None = None,
) -> list[ConcentrationItem]:
    """지역 단위로 집중률 API를 호출해 관광지별 원본 항목 리스트를 전체 페이지에 걸쳐 반환한다.

    baseYmd는 요청 파라미터가 아니다 — 한 번 호출하면 향후 30일치가 자동 포함된다.
    필요한 페이지 수는 첫 페이지 응답의 totalCount 기준으로 동적으로 계산한다(고정 페이지
    수를 정상 종료 조건으로 쓰지 않는다) — 다만 그 값이 안전 상한(_HARD_MAX_PAGES)을
    넘으면 비정상 응답으로 보고 즉시 실패시킨다. 중간 페이지가 예상과 달리 비면 재시도하고,
    그래도 최종 수집 건수가 totalCount에 못 미치면 부분 결과를 "완료"로 반환하지 않고
    예외를 던진다 — analysis 서비스가 이걸 잡아서 analysis_status="failed"로 처리한다.
    """
    if not settings.CONCENTRATION_API_KEY:
        raise ConcentrationApiError(
            "CONCENTRATION_API_KEY가 설정되어 있지 않습니다.", result_code=None, retryable=False
        )

    # 공공데이터포털 "Encoding" 키(이미 %-인코딩됨)를 그대로 넣는 경우가 흔한데,
    # httpx가 params를 다시 인코딩하면서 %2B 등이 %252B로 이중 인코딩되어 403이 난다.
    # unquote()는 인코딩 안 된 키에는 영향이 없으므로 항상 걸어도 안전하다.
    service_key = unquote(settings.CONCENTRATION_API_KEY)

    items, total_count = _fetch_page_with_retry(area_cd, signgu_cd, service_key, 1, tourist_name)
    all_items: list[ConcentrationItem] = list(items)

    if len(all_items) < total_count:
        required_pages = math.ceil(total_count / _PAGE_SIZE)
        if required_pages > _HARD_MAX_PAGES:
            raise ConcentrationApiError(
                f"예상 페이지 수가 안전 한도를 초과했습니다(expected_pages={required_pages})",
                result_code=None,
                retryable=False,
            )
        for page_no in range(2, required_pages + 1):
            items, page_total_count = _fetch_page_with_retry(
                area_cd, signgu_cd, service_key, page_no, tourist_name
            )
            if page_total_count != total_count:
                # 페이지를 여러 번 나눠 부르는 동안 원본 데이터가 갱신되면(드묾) totalCount가
                # 페이지마다 달라질 수 있다 — 이걸 무시하고 계속 모으면 처음 계산한 페이지
                # 수·완결성 검증 기준이 이미 낡은 값이 돼서, 실제로는 불완전한 결과를
                # "완료"로 반환할 위험이 있다. 조용히 넘어가지 않고 재시도 가능한 실패로 던진다.
                raise ConcentrationApiError(
                    f"페이지 조회 중 totalCount가 변경되었습니다"
                    f"(1페이지={total_count}, {page_no}페이지={page_total_count})",
                    result_code=None,
                    retryable=True,
                )
            all_items.extend(items)

    if len(all_items) < total_count:
        raise ConcentrationApiError(
            f"집중률 데이터를 끝까지 수집하지 못했습니다(expected={total_count}, actual={len(all_items)})",
            result_code=None,
            retryable=True,
        )

    return all_items
