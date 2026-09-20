"""마이페이지에서 쓰는 /users/me, /users/me/stats 라우터를 dependency override 로 검증한다."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

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
        id=uuid4(),
        email="tester@example.com",
        nickname="테스터",
        profile_image_url=None,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield
    app.dependency_overrides.clear()


def test_get_me_returns_current_user_profile(client):
    res = client.get("/api/users/me")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["email"] == "tester@example.com"
    assert body["nickname"] == "테스터"
    assert body["profileImageUrl"] is None


def test_get_me_stats_returns_total_and_confirmed_counts(client):
    with patch("app.services.user_service.TripRepository") as MockTripRepo:
        MockTripRepo.return_value.count_stats.return_value = (12, 8)

        res = client.get("/api/users/me/stats")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["totalTripCount"] == 12
    assert body["confirmedTripCount"] == 8


def test_update_me_updates_nickname(client):
    profile = MagicMock(id=uuid4(), nickname="새닉네임", profile_image_url=None)
    with patch("app.services.user_service.UserRepository") as MockUserRepo:
        MockUserRepo.return_value.get_by_id.return_value = profile
        MockUserRepo.return_value.update.return_value = profile

        res = client.patch("/api/users/me", json={"nickname": "새닉네임"})

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["nickname"] == "새닉네임"
    MockUserRepo.return_value.update.assert_called_once()
    _, kwargs = MockUserRepo.return_value.update.call_args
    assert kwargs["nickname"] == "새닉네임"
    assert kwargs["update_image"] is False


def test_update_me_missing_profile_returns_404(client):
    with patch("app.services.user_service.UserRepository") as MockUserRepo:
        MockUserRepo.return_value.get_by_id.return_value = None

        res = client.patch("/api/users/me", json={"nickname": "새닉네임"})

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "USER_NOT_FOUND"


def test_delete_me_removes_auth_user_after_detaching_references(client):
    with patch("app.services.user_service.UserRepository") as MockUserRepo, patch(
        "app.services.user_service.delete_auth_user"
    ) as mock_delete:
        res = client.delete("/api/users/me")

    assert res.status_code == 204
    MockUserRepo.return_value.detach_auth_references.assert_called_once()
    mock_delete.assert_called_once()


def test_delete_me_returns_502_when_auth_delete_fails(client):
    with patch("app.services.user_service.UserRepository"), patch(
        "app.services.user_service.delete_auth_user", side_effect=RuntimeError("boom")
    ):
        res = client.delete("/api/users/me")

    assert res.status_code == 502
