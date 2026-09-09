"""auth / home / schedules API 단위 테스트 (의존성 오버라이드)."""
from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.db.session import get_db
from app.main import app
from app.schemas.auth import AuthSessionResponse, MessageResponse, SignupResponse
from app.schemas.home import HomeResponse, HomeUserResponse, ScheduleSummary
from app.schemas.schedule import PlaceResponse, ScheduleListResponse, ScheduleResponse
from app.schemas.user import CurrentUser, UserResponse
from app.services.auth_service import AuthService
from app.services.home_service import HomeService
from app.services.schedule_service import ScheduleService
from app.services.user_service import UserService


@pytest.fixture
def current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="tester@example.com",
        nickname="테스터",
        profile_image_url=None,
    )


@pytest.fixture
def client(current_user: CurrentUser):
    def _override_user() -> CurrentUser:
        return current_user

    def _override_db():
        yield MagicMock()

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health():
    with TestClient(app) as test_client:
        response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_me(client: TestClient, current_user: CurrentUser, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        UserService,
        "get_me",
        lambda self, user: UserResponse(
            id=user.id,
            email=user.email,
            nickname=user.nickname,
            profile_image_url=user.profile_image_url,
        ),
    )
    response = client.get("/api/users/me")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(current_user.id)
    assert body["nickname"] == "테스터"
    assert body["email"] == "tester@example.com"


def test_get_home(client: TestClient, current_user: CurrentUser, monkeypatch: pytest.MonkeyPatch):
    schedule_id = uuid4()

    def _fake_home(self, user: CurrentUser) -> HomeResponse:
        return HomeResponse(
            user=HomeUserResponse(id=user.id, nickname=user.nickname),
            draft_schedule=ScheduleSummary(
                schedule_id=schedule_id,
                title="제주 1박",
                travel_date=date(2026, 9, 1),
                status="DRAFT",
            ),
            recent_schedules=[],
        )

    monkeypatch.setattr(HomeService, "get_home", _fake_home)
    response = client.get("/api/home")
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["nickname"] == "테스터"
    assert body["draftSchedule"]["scheduleId"] == str(schedule_id)
    assert body["draftSchedule"]["title"] == "제주 1박"
    assert body["recentSchedules"] == []


def test_list_schedules_owner_scoped(
    client: TestClient,
    current_user: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
):
    schedule_id = uuid4()

    def _fake_list(self, user: CurrentUser) -> ScheduleListResponse:
        assert user.id == current_user.id
        return ScheduleListResponse(
            items=[
                ScheduleResponse(
                    id=schedule_id,
                    title="서울 당일",
                    travel_date=None,
                    region_code="SEOUL",
                    status="DRAFT",
                    places=[
                        PlaceResponse(
                            id=uuid4(),
                            name="경복궁",
                            latitude=37.5796,
                            longitude=126.9770,
                            address=None,
                            order_index=0,
                            stay_minutes=90,
                            external_id=None,
                        )
                    ],
                )
            ]
        )

    monkeypatch.setattr(ScheduleService, "list_schedules", _fake_list)
    response = client.get("/api/schedules")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(schedule_id)
    assert body["items"][0]["places"][0]["name"] == "경복궁"


def test_signup_delegates_to_service(monkeypatch: pytest.MonkeyPatch):
    user_id = uuid4()

    def _signup(self, payload) -> SignupResponse:
        return SignupResponse(
            user=UserResponse(
                id=user_id,
                email=payload.email,
                nickname=payload.nickname,
                profile_image_url=None,
            ),
            access_token="access",
            refresh_token="refresh",
            token_type="bearer",
        )

    monkeypatch.setattr(AuthService, "signup", _signup)
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/signup",
            json={"email": "new@example.com", "password": "secret12", "nickname": "신규"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["accessToken"] == "access"


def test_login_delegates_to_service(monkeypatch: pytest.MonkeyPatch):
    user_id = uuid4()

    def _login(self, payload) -> AuthSessionResponse:
        return AuthSessionResponse(
            user=UserResponse(
                id=user_id,
                email=payload.email,
                nickname="테스터",
                profile_image_url=None,
            ),
            access_token="access",
            refresh_token="refresh",
            token_type="bearer",
        )

    monkeypatch.setattr(AuthService, "login", _login)
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/login",
            json={"email": "tester@example.com", "password": "secret12"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "tester@example.com"
    assert body["accessToken"] == "access"


def test_logout(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(AuthService, "logout", lambda self, token: None)
    response = client.post("/api/auth/logout", headers={"Authorization": "Bearer token"})
    assert response.status_code == 204


def test_password_reset_request(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        AuthService,
        "request_password_reset",
        lambda self, payload: MessageResponse(message="비밀번호 재설정 안내를 보냈습니다."),
    )
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/auth/password/reset-request",
            json={"email": "user@example.com"},
        )
    assert response.status_code == 200
    assert "보냈습니다" in response.json()["message"]
