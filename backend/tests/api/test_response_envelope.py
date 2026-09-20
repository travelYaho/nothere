"""공통 응답 포맷({"data",...}/{"error":...}) 리팩토링 회귀 테스트.

프론트가 아직 어떤 API 도 실제로 호출하지 않는 상태(로그인/홈 화면은 하드코딩된
목업 데이터만 쓴다)라, "기존 API가 새 포맷에서도 정상 동작"을 프론트로는 검증할
수 없다. 대신 FastAPI TestClient + dependency override 로 라우터가 실제로
{"data": ...}/{"error": ...} 로 감싸서 응답하는지 백엔드 레벨에서 확인한다.
"""
import asyncio
import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppError, ErrorCode
from app.core.security import get_current_user
from app.db.session import get_db
from app.main import app, app_error_handler, db_error_handler, validation_error_handler
from app.schemas.user import CurrentUser


# --- 1. 예외 핸들러 단위 테스트 (DB/네트워크 불필요) ---

def test_app_error_handler_wraps_under_error_key():
    exc = AppError(ErrorCode.USER_NOT_FOUND, "사용자를 찾을 수 없습니다.", status_code=404)
    response = asyncio.run(app_error_handler(None, exc))
    body = json.loads(response.body)
    assert response.status_code == 404
    assert body == {"error": {"code": "USER_NOT_FOUND", "message": "사용자를 찾을 수 없습니다."}}


def test_db_error_handler_wraps_under_error_key():
    response = asyncio.run(db_error_handler(None, SQLAlchemyError("boom")))
    body = json.loads(response.body)
    assert response.status_code == 500
    assert body == {
        "error": {"code": ErrorCode.DB_ERROR, "message": "데이터베이스 오류가 발생했습니다."}
    }


def test_validation_error_handler_wraps_under_error_key():
    exc = RequestValidationError(
        errors=[{"loc": ("body", "email"), "msg": "field required", "type": "missing"}]
    )
    response = asyncio.run(validation_error_handler(None, exc))
    body = json.loads(response.body)
    assert response.status_code == 422
    assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR
    assert "email" in body["error"]["message"]


# --- 2. 라우터 통합 테스트 (dependency override, DB/Supabase 실접속 불필요) ---

@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_get_users_me_returns_data_envelope(client):
    fake_user = CurrentUser(
        id=uuid4(), email="tester@example.com", nickname="테스터", profile_image_url=None
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    res = client.get("/api/users/me")

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["nickname"] == "테스터"
    assert body["data"]["email"] == "tester@example.com"
    # camelCase 변환은 그대로 유지되는지 확인
    assert "profileImageUrl" in body["data"]


def test_get_home_returns_data_envelope_with_null_draft(client):
    fake_user = CurrentUser(
        id=uuid4(), email="tester@example.com", nickname="테스터", profile_image_url=None
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: MagicMock()

    with patch("app.services.home_service.TripRepository") as MockRepo, patch(
        "app.services.home_service.GuideRepository"
    ) as MockGuideRepo:
        MockRepo.return_value.get_in_progress.return_value = None
        MockRepo.return_value.get_recent.return_value = []
        MockGuideRepo.return_value.get_top_public.return_value = None

        res = client.get("/api/home")

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["user"]["nickname"] == "테스터"
    assert body["data"]["draftSchedule"] is None
    assert body["data"]["recentSchedules"] == []


def test_missing_auth_token_returns_error_envelope(client):
    res = client.get("/api/users/me")

    assert res.status_code == 401
    body = res.json()
    assert body["error"]["code"] == ErrorCode.AUTH_TOKEN_MISSING


def test_signup_validation_error_returns_error_envelope(client):
    res = client.post(
        "/api/auth/signup",
        json={"email": "not-an-email", "password": "123", "nickname": ""},
    )

    assert res.status_code == 422
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR
