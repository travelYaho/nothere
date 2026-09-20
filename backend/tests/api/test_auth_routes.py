"""OAuth profile 보정 엔드포인트 계약을 검증한다."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthUser, get_auth_user
from app.db.session import get_db
from app.main import app
from app.schemas.user import UserResponse


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _auth_override():
    fake_user = AuthUser(id=uuid4(), email="kakao@example.com", user_metadata={}, identities=[])
    app.dependency_overrides[get_auth_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield
    app.dependency_overrides.clear()


def test_ensure_profile_returns_user_payload(client):
    user_id = uuid4()
    with patch("app.api.auth.AuthService") as MockService:
        MockService.return_value.ensure_profile.return_value = UserResponse(
            id=user_id,
            email="kakao@example.com",
            nickname="말고마니",
            profile_image_url=None,
        )

        res = client.post("/api/auth/ensure-profile")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["email"] == "kakao@example.com"
    assert body["nickname"] == "말고마니"
    assert body["profileImageUrl"] is None
