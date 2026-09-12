"""집중률 API 클라이언트(concentration_api.py) 단위 테스트.

실제 네트워크 호출은 전부 monkeypatch로 대체한다.
"""
import httpx
import pytest

from app.clients import concentration_api
from app.core.config import settings


def _response(json_body: dict) -> httpx.Response:
    return httpx.Response(200, json=json_body, request=httpx.Request("GET", "https://example.com"))


def _header(result_code: str = "0000") -> dict:
    return {"resultCode": result_code, "resultMsg": "OK"}


def test_fetch_concentration_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "")

    with pytest.raises(concentration_api.ConcentrationApiError):
        concentration_api.fetch_concentration("11", "11110")


def test_fetch_concentration_returns_empty_list_when_total_count_zero(monkeypatch):
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return _response({"response": {"header": _header(), "body": {"totalCount": 0, "items": ""}}})

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert concentration_api.fetch_concentration("11", "99999") == []


def test_fetch_concentration_raises_on_unknown_items_shape(monkeypatch):
    """items가 dict도, 확인된 빈 문자열 모양도 아니면(예: 숫자) 재시도 없이 즉시 실패한다."""
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return _response({"response": {"header": _header(), "body": {"totalCount": 5, "items": 12345}}})

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(concentration_api.ConcentrationApiError):
        concentration_api.fetch_concentration("11", "11110")


def test_fetch_concentration_single_page_collects_all_items(monkeypatch):
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        items = [
            {"tAtsNm": "경복궁", "areaCd": "11", "signguCd": "11110", "baseYmd": "20260101", "cnctrRate": "10.5"}
        ]
        return _response(
            {"response": {"header": _header(), "body": {"totalCount": 1, "items": {"item": items}}}}
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    result = concentration_api.fetch_concentration("11", "11110")
    assert len(result) == 1
    assert result[0].tourist_name == "경복궁"
    assert result[0].raw_value == 10.5


def test_fetch_concentration_dynamically_paginates_by_total_count(monkeypatch):
    """totalCount=250, PAGE_SIZE=100 이면 페이지 3개(고정 상한이 아니라 계산된 값)만 호출한다."""
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")
    calls = []

    def _fake_get(url, params=None, **kwargs):
        page_no = params["pageNo"]
        calls.append(page_no)
        # 총 250건을 100/100/50으로 나눠 돌려준다.
        count_this_page = 100 if page_no < 3 else 50
        items = [
            {"tAtsNm": f"장소{page_no}-{i}", "areaCd": "11", "signguCd": "11110", "baseYmd": "20260101", "cnctrRate": "1.0"}
            for i in range(count_this_page)
        ]
        return _response(
            {"response": {"header": _header(), "body": {"totalCount": 250, "items": {"item": items}}}}
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    result = concentration_api.fetch_concentration("11", "11110")

    assert calls == [1, 2, 3]
    assert len(result) == 250


def test_fetch_concentration_retries_unexpectedly_empty_page_then_succeeds(monkeypatch):
    """총 200건인데 2페이지가 한 번 비어 오면(일시적 장애) 재시도해서 결국 다 모은다."""
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")
    attempts = {"page2": 0}

    def _fake_get(url, params=None, **kwargs):
        page_no = params["pageNo"]
        if page_no == 1:
            items = [
                {"tAtsNm": f"장소1-{i}", "areaCd": "11", "signguCd": "11110", "baseYmd": "20260101", "cnctrRate": "1.0"}
                for i in range(100)
            ]
            return _response(
                {"response": {"header": _header(), "body": {"totalCount": 200, "items": {"item": items}}}}
            )
        attempts["page2"] += 1
        if attempts["page2"] == 1:
            # 첫 시도는 비정상적으로 빈 페이지
            return _response({"response": {"header": _header(), "body": {"totalCount": 200, "items": ""}}})
        items = [
            {"tAtsNm": f"장소2-{i}", "areaCd": "11", "signguCd": "11110", "baseYmd": "20260101", "cnctrRate": "1.0"}
            for i in range(100)
        ]
        return _response(
            {"response": {"header": _header(), "body": {"totalCount": 200, "items": {"item": items}}}}
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    result = concentration_api.fetch_concentration("11", "11110")

    assert len(result) == 200
    assert attempts["page2"] == 2


def test_fetch_concentration_raises_when_still_incomplete_after_retries(monkeypatch):
    """재시도해도 계속 비면 부분 결과를 완료로 반환하지 않고 예외를 던진다."""
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(url, params=None, **kwargs):
        page_no = params["pageNo"]
        if page_no == 1:
            items = [
                {"tAtsNm": f"장소{i}", "areaCd": "11", "signguCd": "11110", "baseYmd": "20260101", "cnctrRate": "1.0"}
                for i in range(100)
            ]
            return _response(
                {"response": {"header": _header(), "body": {"totalCount": 200, "items": {"item": items}}}}
            )
        # 2페이지는 계속 비어 온다(재시도해도 회복 안 됨)
        return _response({"response": {"header": _header(), "body": {"totalCount": 200, "items": ""}}})

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(concentration_api.ConcentrationApiError):
        concentration_api.fetch_concentration("11", "11110")


def test_fetch_concentration_raises_when_required_pages_exceed_hard_limit(monkeypatch):
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        # totalCount가 비정상적으로 커서 필요한 페이지 수가 안전 상한을 넘는다.
        return _response(
            {"response": {"header": _header(), "body": {"totalCount": 10_000_000, "items": ""}}}
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(concentration_api.ConcentrationApiError):
        concentration_api.fetch_concentration("11", "11110")


def test_result_code_03_returns_empty_list_without_error(monkeypatch):
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return _response({"response": {"header": _header("03"), "body": {}}})

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert concentration_api.fetch_concentration("11", "11110") == []


def test_result_code_30_raises_non_retryable_error(monkeypatch):
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return _response({"response": {"header": _header("30"), "body": {}}})

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(concentration_api.ConcentrationApiError) as exc_info:
        concentration_api.fetch_concentration("11", "11110")
    assert exc_info.value.retryable is False


# --- 비정상 응답 구조 (JSON 파싱 실패 외 나머지) ---

def test_raises_when_response_is_not_valid_json(monkeypatch):
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(200, text="이것은 JSON이 아닙니다", request=httpx.Request("GET", "https://example.com"))

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(concentration_api.ConcentrationApiError):
        concentration_api.fetch_concentration("11", "11110")


def test_raises_when_body_is_explicitly_null(monkeypatch):
    """response.body가 JSON에서 명시적으로 null이면 .get(key, default)의 default가 적용되지
    않아 None을 그대로 돌려준다 — 이후 .get() 호출에서 AttributeError로 이어지는지 확인."""
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return _response({"response": {"header": _header(), "body": None}})

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(concentration_api.ConcentrationApiError):
        concentration_api.fetch_concentration("11", "11110")


def test_raises_when_items_item_is_explicitly_null(monkeypatch):
    """items.item이 명시적으로 null이면 순회 시도에서 TypeError로 이어진다."""
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return _response(
            {"response": {"header": _header(), "body": {"totalCount": 1, "items": {"item": None}}}}
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(concentration_api.ConcentrationApiError):
        concentration_api.fetch_concentration("11", "11110")


def test_raises_when_item_list_contains_non_object_element(monkeypatch):
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return _response(
            {
                "response": {
                    "header": _header(),
                    "body": {"totalCount": 2, "items": {"item": [{"tAtsNm": "경복궁"}, "이상한문자열원소"]}},
                }
            }
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(concentration_api.ConcentrationApiError):
        concentration_api.fetch_concentration("11", "11110")


def test_raises_when_total_count_is_negative(monkeypatch):
    """int() 변환 자체는 성공하지만 의미가 없는 값이라 별도로 검증한다."""
    monkeypatch.setattr(settings, "CONCENTRATION_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return _response({"response": {"header": _header(), "body": {"totalCount": -5, "items": ""}}})

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(concentration_api.ConcentrationApiError):
        concentration_api.fetch_concentration("11", "11110")
