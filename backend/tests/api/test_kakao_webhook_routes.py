"""카카오 연결 해제 웹훅 HTTP 계약을 검증한다."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import get_db
from app.main import app

UNLINK_PATH = "/api/auth/kakao/unlink"
ADMIN_KEY = "test-kakao-admin"


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def admin_key():
    with patch.object(settings, "KAKAO_ADMIN_KEY", ADMIN_KEY):
        yield ADMIN_KEY


def _auth(key: str) -> dict[str, str]:
    return {"Authorization": f"KakaoAK {key}"}


def test_unlink_rejects_missing_authorization(client, admin_key):
    res = client.get(UNLINK_PATH, params={"user_id": "1", "app_id": "2"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_unlink_rejects_wrong_admin_key(client, admin_key):
    res = client.get(
        UNLINK_PATH,
        params={"user_id": "1"},
        headers=_auth("wrong-key"),
    )
    assert res.status_code == 401


def test_unlink_get_returns_200_and_deletes_user(client, admin_key):
    with patch("app.api.auth.KakaoWebhookService") as MockService:
        res = client.get(
            UNLINK_PATH,
            params={"user_id": "123456", "app_id": "99", "referrer_type": "UNLINK_FROM_APPS"},
            headers=_auth(admin_key),
        )

    assert res.status_code == 200
    MockService.return_value.unlink.assert_called_once_with("123456")


def test_unlink_post_form_returns_200(client, admin_key):
    with patch("app.api.auth.KakaoWebhookService") as MockService:
        res = client.post(
            UNLINK_PATH,
            data={"user_id": "123456", "app_id": "99", "referrer_type": "UNLINK_FROM_ADMIN"},
            headers=_auth(admin_key),
        )

    assert res.status_code == 200
    MockService.return_value.unlink.assert_called_once_with("123456")


def test_unlink_returns_200_when_processing_fails(client, admin_key):
    with patch("app.api.auth.KakaoWebhookService") as MockService:
        MockService.return_value.unlink.side_effect = RuntimeError("db down")
        res = client.get(
            UNLINK_PATH,
            params={"user_id": "123456"},
            headers=_auth(admin_key),
        )

    assert res.status_code == 200


def test_unlink_returns_200_when_user_id_missing(client, admin_key):
    with patch("app.api.auth.KakaoWebhookService") as MockService:
        res = client.get(UNLINK_PATH, headers=_auth(admin_key))

    assert res.status_code == 200
    MockService.return_value.unlink.assert_not_called()
