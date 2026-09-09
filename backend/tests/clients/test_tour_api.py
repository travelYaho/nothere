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

    def _fake_get(url, params=None, timeout=None):
        captured["params"] = params
        return httpx.Response(
            200,
            json={"response": {"body": {"totalCount": 0, "items": ""}}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    tour_api.search_places("궁", area_code="1")

    assert captured["params"]["areaCode"] == "1"
