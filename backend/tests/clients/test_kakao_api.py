"""Kakao 로컬 주소 검색 클라이언트(geocode_address)를 httpx 모킹으로 검증한다."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.clients import kakao_api
from app.core.exceptions import AppError, ErrorCode


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setattr(kakao_api.settings, "KAKAO_REST_API_KEY", "test-key")


def _doc(lat="37.5776", lng="126.9938", address_type="ROAD_ADDR", name="서울 종로구 창경궁로 185"):
    return {"address_type": address_type, "address_name": name, "y": lat, "x": lng}


def _response(payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    return response


def _geocode(payload, status_code=200):
    with patch("app.clients.kakao_api.httpx.get", return_value=_response(payload, status_code)):
        return kakao_api.geocode_address("서울 종로구 창경궁로 185")


def test_geocode_maps_y_to_latitude_and_x_to_longitude():
    result = _geocode({"documents": [_doc(lat="37.5", lng="126.9")]})

    assert result.latitude == 37.5
    assert result.longitude == 126.9


def test_geocode_returns_none_when_no_documents():
    assert _geocode({"documents": []}) is None
    assert _geocode({}) is None


def test_geocode_ignores_region_level_results_because_they_are_not_building_coordinates():
    assert _geocode({"documents": [_doc(address_type="REGION")]}) is None


def test_geocode_accepts_jibun_address_results():
    result = _geocode({"documents": [_doc(address_type="REGION_ADDR")]})

    assert result is not None


def test_geocode_multiple_results_use_the_one_that_exactly_matches_the_query():
    # 실제 응답 형태: "종로 1"을 검색하면 정확히 일치하는 주소 뒤로 다른 도로의 유사 결과가 따라온다.
    payload = {
        "documents": [
            _doc(lat="37.571", lng="126.978", name="서울 종로구 종로 1"),
            _doc(lat="37.5714", lng="127.0065", name="서울 종로구 종로41길 1"),
            _doc(lat="37.573", lng="127.006", name="서울 종로구 종로41나길 1"),
        ]
    }
    with patch("app.clients.kakao_api.httpx.get", return_value=_response(payload)):
        result = kakao_api.geocode_address("서울 종로구  종로 1")

    assert result.latitude == 37.571


def test_geocode_multiple_results_without_an_exact_match_are_rejected():
    payload = {
        "documents": [
            _doc(name="서울 종로구 종로12길 10"),
            _doc(lat="37.5698", lng="126.9932", name="서울 종로구 종로22길 10"),
        ]
    }
    with patch("app.clients.kakao_api.httpx.get", return_value=_response(payload)):
        with pytest.raises(AppError) as exc_info:
            kakao_api.geocode_address("서울 종로구 종로 10")

    assert exc_info.value.code == ErrorCode.ADDRESS_NOT_FOUND
    assert exc_info.value.status_code == 400


def test_geocode_nearby_results_are_not_treated_as_the_same_place():
    # 가까운 두 결과가 같은 주소 문자열을 가져도(정확히 일치가 둘) 하나로 합치지 않고 거절한다.
    with pytest.raises(AppError) as exc_info:
        _geocode({"documents": [_doc(lat="37.5776", lng="126.9938"), _doc(lat="37.5777", lng="126.9939")]})

    assert exc_info.value.code == ErrorCode.ADDRESS_NOT_FOUND
    assert exc_info.value.status_code == 400


def test_geocode_results_at_different_points_are_rejected_as_ambiguous():
    with pytest.raises(AppError) as exc_info:
        _geocode({"documents": [_doc(lat="37.5776", lng="126.9938"), _doc(lat="35.1591", lng="129.1603")]})

    assert exc_info.value.code == ErrorCode.ADDRESS_NOT_FOUND
    assert exc_info.value.status_code == 400


@pytest.mark.parametrize(
    "lat,lng",
    [("nan", "126.9"), ("37.5", "inf"), ("91", "126.9"), ("37.5", "181"), ("-91", "126.9"), ("abc", "126.9")],
)
def test_geocode_rejects_invalid_coordinates_from_response(lat, lng):
    with pytest.raises(AppError) as exc_info:
        _geocode({"documents": [_doc(lat=lat, lng=lng)]})

    assert exc_info.value.code == ErrorCode.EXTERNAL_API_UNAVAILABLE
    assert exc_info.value.status_code == 503


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "text",
        {"documents": "text"},
        {"documents": 5},
        {"documents": {}},
        {"documents": ["text"]},
        {"documents": [{"address_type": "ROAD_ADDR"}]},
    ],
)
def test_geocode_rejects_malformed_response_structure(payload):
    with pytest.raises(AppError) as exc_info:
        _geocode(payload)

    assert exc_info.value.code == ErrorCode.EXTERNAL_API_UNAVAILABLE
    assert exc_info.value.status_code == 503


def test_geocode_http_error_status_becomes_503():
    with pytest.raises(AppError) as exc_info:
        _geocode({"errorType": "NotAuthorizedError"}, status_code=403)

    assert exc_info.value.code == ErrorCode.EXTERNAL_API_UNAVAILABLE
    assert exc_info.value.status_code == 503


def test_geocode_timeout_becomes_503():
    with patch("app.clients.kakao_api.httpx.get", side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(AppError) as exc_info:
            kakao_api.geocode_address("서울 종로구 창경궁로 185")

    assert exc_info.value.code == ErrorCode.EXTERNAL_API_UNAVAILABLE
    assert exc_info.value.status_code == 503


def test_geocode_non_json_body_becomes_503():
    response = _response(None)
    response.json.side_effect = ValueError("not json")
    with patch("app.clients.kakao_api.httpx.get", return_value=response):
        with pytest.raises(AppError) as exc_info:
            kakao_api.geocode_address("서울 종로구 창경궁로 185")

    assert exc_info.value.status_code == 503


def test_geocode_without_api_key_becomes_503_without_calling_kakao(monkeypatch):
    monkeypatch.setattr(kakao_api.settings, "KAKAO_REST_API_KEY", "")
    with patch("app.clients.kakao_api.httpx.get") as get:
        with pytest.raises(AppError) as exc_info:
            kakao_api.geocode_address("서울 종로구 창경궁로 185")

    assert exc_info.value.status_code == 503
    get.assert_not_called()
