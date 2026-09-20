"""OAuth 직후 profile 보정과 닉네임/아바타 추출을 검증한다."""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppError, ErrorCode
from app.core.security import AuthUser
from app.services.auth_service import AuthService, avatar_from_auth_user, nickname_from_auth_user


def _auth_user(**overrides) -> AuthUser:
    return AuthUser(
        id=overrides.get("id", uuid4()),
        email=overrides.get("email", "kakao@example.com"),
        user_metadata=overrides.get("user_metadata", {}),
        identities=overrides.get("identities", []),
    )


def test_nickname_prefers_kakao_metadata_over_email():
    auth_user = _auth_user(
        user_metadata={"kakao_account": {"profile": {"nickname": "말고마니"}}},
    )
    assert nickname_from_auth_user(auth_user) == "말고마니"


def test_nickname_falls_back_to_email_local_part_then_default():
    assert nickname_from_auth_user(_auth_user(email="traveler@kakao.com")) == "traveler"
    assert nickname_from_auth_user(_auth_user(email="")) == "카카오 사용자"


def test_avatar_reads_picture_from_identity_data():
    auth_user = _auth_user(
        identities=[{"identity_data": {"picture": "https://img.example/a.png"}}],
    )
    assert avatar_from_auth_user(auth_user) == "https://img.example/a.png"


def test_ensure_profile_returns_existing_row_without_creating():
    existing = MagicMock(id=uuid4(), nickname="기존", profile_image_url=None)
    service = AuthService(db=MagicMock())
    service.users = MagicMock()
    service.users.get_by_id.return_value = existing

    auth_user = _auth_user(id=existing.id, email="a@b.com")
    result = service.ensure_profile(auth_user)

    assert result.nickname == "기존"
    service.users.create.assert_not_called()


def test_ensure_profile_creates_from_oauth_metadata():
    created = MagicMock(
        id=uuid4(),
        nickname="말고마니",
        profile_image_url="https://img.example/a.png",
    )
    service = AuthService(db=MagicMock())
    service.users = MagicMock()
    service.users.get_by_id.return_value = None
    service.users.create.return_value = created

    auth_user = _auth_user(
        id=created.id,
        user_metadata={"nickname": "말고마니", "avatar_url": "https://img.example/a.png"},
    )
    result = service.ensure_profile(auth_user)

    service.users.create.assert_called_once_with(
        user_id=created.id,
        nickname="말고마니",
        profile_image_url="https://img.example/a.png",
    )
    assert result.id == created.id
    assert result.nickname == "말고마니"
    assert result.profile_image_url == "https://img.example/a.png"


def test_ensure_profile_recovers_when_create_races_to_existing_row():
    existing = MagicMock(id=uuid4(), nickname="기존", profile_image_url=None)
    service = AuthService(db=MagicMock())
    service.users = MagicMock()
    service.users.get_by_id.side_effect = [None, existing]
    service.users.create.side_effect = SQLAlchemyError("duplicate")

    result = service.ensure_profile(_auth_user(id=existing.id))

    service.db.rollback.assert_called_once()
    assert result.nickname == "기존"


def test_ensure_profile_raises_when_create_fails_and_row_still_missing():
    service = AuthService(db=MagicMock())
    service.users = MagicMock()
    service.users.get_by_id.return_value = None
    service.users.create.side_effect = SQLAlchemyError("db down")

    with pytest.raises(AppError) as exc:
        service.ensure_profile(_auth_user())

    assert exc.value.code == ErrorCode.DB_ERROR
    assert exc.value.status_code == 500
