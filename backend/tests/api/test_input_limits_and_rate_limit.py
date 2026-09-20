"""입력 길이 상한과 요청 횟수 제한을 라우터 단에서 검증한다.

길이 검증은 서비스/DB 에 닿기 전에 pydantic 이 막으므로 422 만 확인하면 된다.
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import SEARCH_LIMIT, limiter
from app.core.security import get_current_user
from app.db.session import get_db
from app.main import app
from app.schemas.user import CurrentUser


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _auth_override():
    fake_user = CurrentUser(
        id=uuid4(), email="tester@example.com", nickname="테스터", profile_image_url=None
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield
    app.dependency_overrides.clear()


def test_search_keyword_over_50_chars_returns_422(client):
    res = client.get("/api/places/search", params={"keyword": "가" * 51})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_search_keyword_empty_returns_422(client):
    res = client.get("/api/places/search", params={"keyword": ""})
    assert res.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "가" * 101, "address": "서울 종로구 사직로 161"},
        {"name": "   ", "address": "서울 종로구 사직로 161"},
        {"name": "장소", "address": "서울 종로구 사직로 161 " + "가" * 200},
    ],
)
def test_custom_place_length_limits_return_422(client, payload):
    res = client.post(f"/api/trips/{uuid4()}/places/custom", json=payload)
    assert res.status_code == 422


def test_create_trip_title_over_100_chars_returns_422(client):
    res = client.post(
        "/api/trips",
        json={
            "title": "가" * 101,
            "travelDate": "2099-01-01",
            "regionId": 1,
            "preferredExperienceTagIds": [1, 2],
        },
    )
    assert res.status_code == 422


def test_search_rate_limit_returns_429_error_envelope(client):
    limiter.enabled = True
    limiter.reset()
    try:
        with patch("app.services.place_service.PlaceService.search_places") as mock_search:
            mock_search.return_value = {"places": []}
            limit = int(SEARCH_LIMIT.split("/")[0])
            statuses = [
                client.get("/api/places/search", params={"keyword": "경복궁"}).status_code
                for _ in range(limit + 1)
            ]
        res = client.get("/api/places/search", params={"keyword": "경복궁"})
    finally:
        limiter.enabled = False
        limiter.reset()

    assert statuses[:limit] == [200] * limit
    assert statuses[limit] == 429
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "RATE_LIMITED"
