"""TourAPI 클라이언트가 키 없음/호출 실패 상황에서 500이 아니라
EXTERNAL_API_UNAVAILABLE(503)로 명확히 실패하는지 검증한다.

실제 네트워크 호출은 전부 monkeypatch 로 대체해서, 지금처럼 TOUR_API_KEY 가
없는 환경에서도 (그리고 있더라도) 결정적으로 돌아간다.
"""
import httpx
import pytest

from app.clients import tour_api
from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode


def test_missing_key_raises_503_without_calling_network(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "")

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("키가 없으면 실제 HTTP 호출을 시도하면 안 된다")

    monkeypatch.setattr(httpx, "get", _fail_if_called)

    with pytest.raises(AppError) as exc_info:
        tour_api.search_places("경복궁")

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == ErrorCode.EXTERNAL_API_UNAVAILABLE


def test_network_failure_raises_503_not_500(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _raise_connect_error(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", _raise_connect_error)

    with pytest.raises(AppError) as exc_info:
        tour_api.search_places("경복궁")

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == ErrorCode.EXTERNAL_API_UNAVAILABLE


def test_non_2xx_response_raises_503(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(500, request=httpx.Request("GET", "https://example.com"))

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(AppError) as exc_info:
        tour_api.search_places("경복궁")

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == ErrorCode.EXTERNAL_API_UNAVAILABLE


def test_malformed_body_raises_503(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"unexpected": "shape"},
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    with pytest.raises(AppError) as exc_info:
        tour_api.search_places("경복궁")

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == ErrorCode.EXTERNAL_API_UNAVAILABLE


def test_zero_results_returns_empty_list(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"response": {"body": {"totalCount": 0, "items": ""}}},
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert tour_api.search_places("존재하지않는장소") == []


def test_single_result_item_is_not_a_list_but_still_parsed(monkeypatch):
    """TourAPI 는 결과가 1건이면 item 을 배열이 아니라 객체 하나로 내려준다."""
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={
                "response": {
                    "body": {
                        "totalCount": 1,
                        "items": {
                            "item": {
                                "contentid": "12345",
                                "title": "경복궁",
                                "cat3": "역사·문화",
                                "addr1": "서울 종로구",
                                "mapx": "126.977041",
                                "mapy": "37.579617",
                            }
                        },
                    }
                }
            },
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    results = tour_api.search_places("경복궁")

    assert len(results) == 1
    place = results[0]
    assert place.content_id == "12345"
    assert place.name == "경복궁"
    assert place.category == "역사·문화"
    assert place.latitude == pytest.approx(37.579617)
    assert place.longitude == pytest.approx(126.977041)


def test_multiple_result_items_are_all_parsed(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={
                "response": {
                    "body": {
                        "totalCount": 2,
                        "items": {
                            "item": [
                                {"contentid": "1", "title": "경복궁", "mapx": "126.9", "mapy": "37.5"},
                                {"contentid": "2", "title": "창덕궁", "mapx": "126.9", "mapy": "37.5"},
                            ]
                        },
                    }
                }
            },
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    results = tour_api.search_places("궁")

    assert [p.name for p in results] == ["경복궁", "창덕궁"]


def test_area_code_is_forwarded_when_given(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")
    captured = {}

    def _fake_get(url, params=None, timeout=None, **_kwargs):
        captured["params"] = params
        return httpx.Response(
            200,
            json={"response": {"body": {"totalCount": 0, "items": ""}}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    tour_api.search_places("궁", area_code="1")

    assert captured["params"]["areaCode"] == "1"


def test_urlencoded_service_key_is_decoded_before_httpx(monkeypatch):
    monkeypatch.setattr(
        settings,
        "TOUR_API_KEY",
        "abc%2Bdef%3D%3D",
    )
    captured = {}

    def _fake_get(url, params=None, timeout=None, follow_redirects=None):
        captured["params"] = params
        return httpx.Response(
            200,
            json={"response": {"body": {"totalCount": 0, "items": ""}}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    tour_api.search_places("궁")

    assert captured["params"]["serviceKey"] == "abc+def=="


# --- to_signgu_cd ---

def test_to_signgu_cd_concatenates_area_and_signgu():
    assert tour_api.to_signgu_cd("11", "290") == "11290"


def test_to_signgu_cd_preserves_leading_zero():
    assert tour_api.to_signgu_cd("11", "011") == "11011"


def test_to_signgu_cd_returns_none_when_either_missing():
    assert tour_api.to_signgu_cd(None, "290") is None
    assert tour_api.to_signgu_cd("11", None) is None
    assert tour_api.to_signgu_cd("11", "") is None


def test_to_signgu_cd_accepts_already_5_digit_value_when_prefix_matches():
    assert tour_api.to_signgu_cd("11", "11290") == "11290"


def test_to_signgu_cd_rejects_5_digit_value_with_mismatched_prefix():
    assert tour_api.to_signgu_cd("11", "26290") is None


def test_to_signgu_cd_rejects_malformed_short_signgu_cd():
    """5자리가 아니라고 무조건 이어붙이면 "1129" 같은 4자리 값이 나올 수 있었다 — 3자리가
    아니면 형식 오류로 취급한다."""
    assert tour_api.to_signgu_cd("11", "29") is None


def test_to_signgu_cd_rejects_non_numeric_codes():
    assert tour_api.to_signgu_cd("1a", "290") is None
    assert tour_api.to_signgu_cd("11", "2a0") is None


def test_to_signgu_cd_rejects_wrong_length_area_cd():
    assert tour_api.to_signgu_cd("111", "290") is None
    assert tour_api.to_signgu_cd("1", "290") is None


def test_to_signgu_cd_rejects_non_string_codes():
    """TourAPI가 lDongRegnCd를 JSON 숫자로 주면 len()에서 바로 TypeError가 나던 걸 막는다."""
    assert tour_api.to_signgu_cd(11, "290") is None
    assert tour_api.to_signgu_cd("11", 290) is None


# --- fetch_nearby_places 빈/이상 응답 ---

def test_fetch_nearby_places_returns_empty_list_when_items_is_empty_string(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"response": {"header": {"resultCode": "0000"}, "body": {"totalCount": 0, "items": ""}}},
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert tour_api.fetch_nearby_places(37.5, 127.0, 3000) == []


def test_fetch_nearby_places_returns_empty_list_when_response_is_not_valid_json(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(200, text="이것은 JSON이 아닙니다", request=httpx.Request("GET", "https://example.com"))

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert tour_api.fetch_nearby_places(37.5, 127.0, 3000) == []


def test_fetch_nearby_places_returns_empty_list_when_payload_is_a_list(monkeypatch):
    """payload 자체가 dict가 아니면(예: 최상위가 배열) payload.get()에서 AttributeError가
    나던 걸 막는다."""
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(200, json=[1, 2, 3], request=httpx.Request("GET", "https://example.com"))

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert tour_api.fetch_nearby_places(37.5, 127.0, 3000) == []


def test_fetch_nearby_places_returns_empty_list_when_body_is_explicitly_null(monkeypatch):
    """body가 JSON에서 명시적으로 null이면 .get(key, {})의 기본값이 적용 안 되고 None이
    그대로 반환돼 이어지는 .get()에서 AttributeError가 나던 걸 막는다."""
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"response": {"header": {"resultCode": "0000"}, "body": None}},
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert tour_api.fetch_nearby_places(37.5, 127.0, 3000) == []


def test_fetch_nearby_places_returns_empty_list_and_logs_on_unknown_items_shape(monkeypatch, caplog):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"response": {"header": {"resultCode": "0000"}, "body": {"totalCount": 5, "items": 12345}}},
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    with caplog.at_level("WARNING"):
        result = tour_api.fetch_nearby_places(37.5, 127.0, 3000)

    assert result == []
    assert any("items" in record.message for record in caplog.records)


def test_fetch_nearby_places_returns_empty_list_when_item_is_not_list_or_dict(monkeypatch, caplog):
    """items.item이 리스트도 dict도 아니면(예: 숫자) 반복 시 TypeError가 나던 걸 방지한다."""
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={"response": {"header": {"resultCode": "0000"}, "body": {"totalCount": 1, "items": {"item": 12345}}}},
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    with caplog.at_level("WARNING"):
        result = tour_api.fetch_nearby_places(37.5, 127.0, 3000)

    assert result == []
    assert any("items.item" in record.message for record in caplog.records)


def test_fetch_nearby_places_skips_non_dict_elements_in_item_list(monkeypatch):
    """리스트 안에 dict가 아닌 원소(문자열, None)가 섞여도 그 원소만 건너뛰고 정상
    원소는 계속 처리한다(전체를 AttributeError로 날리지 않음)."""
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "0000"},
                    "body": {
                        "totalCount": 3,
                        "items": {
                            "item": [
                                {"contentid": "1", "title": "정상장소", "mapx": "127.0", "mapy": "37.5"},
                                "이상한문자열원소",
                                None,
                            ]
                        },
                    },
                },
            },
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    result = tour_api.fetch_nearby_places(37.5, 127.0, 3000)

    assert len(result) == 1
    assert result[0].name == "정상장소"


def test_fetch_nearby_places_fills_area_cd_and_signgu_cd(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "0000"},
                    "body": {
                        "totalCount": 1,
                        "items": {
                            "item": {
                                "contentid": "294505",
                                "title": "경국사(서울)",
                                "mapx": "127.0056310926",
                                "mapy": "37.6139242251",
                                "lDongRegnCd": "11",
                                "lDongSignguCd": "290",
                                "cat2": "A0201",
                            }
                        },
                    },
                }
            },
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    result = tour_api.fetch_nearby_places(37.6, 127.0, 3000)

    assert len(result) == 1
    assert result[0].area_cd == "11"
    assert result[0].signgu_cd == "11290"
