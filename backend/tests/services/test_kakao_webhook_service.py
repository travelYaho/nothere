"""카카오 연결 해제 웹훅이 회원 삭제로 이어지는지 검증한다."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.services.kakao_webhook_service import KakaoWebhookService, kakao_admin_authorized


def test_kakao_admin_authorized_accepts_matching_key():
    with patch("app.services.kakao_webhook_service.settings") as mock_settings:
        mock_settings.KAKAO_ADMIN_KEY = "secret-admin"
        assert kakao_admin_authorized("KakaoAK secret-admin") is True


def test_kakao_admin_authorized_rejects_wrong_or_missing_key():
    with patch("app.services.kakao_webhook_service.settings") as mock_settings:
        mock_settings.KAKAO_ADMIN_KEY = "secret-admin"
        assert kakao_admin_authorized("KakaoAK other") is False
        assert kakao_admin_authorized("Bearer secret-admin") is False
        assert kakao_admin_authorized(None) is False

        mock_settings.KAKAO_ADMIN_KEY = ""
        assert kakao_admin_authorized("KakaoAK secret-admin") is False


def test_unlink_skips_delete_when_identity_missing():
    db = MagicMock(spec=Session)
    db.execute.return_value.first.return_value = None
    service = KakaoWebhookService(db)

    with patch.object(service.users, "delete_by_user_id") as mock_delete:
        service.unlink("123456")

    mock_delete.assert_not_called()


def test_unlink_deletes_matched_auth_user():
    user_id = uuid4()
    db = MagicMock(spec=Session)
    db.execute.return_value.first.return_value = (user_id,)
    service = KakaoWebhookService(db)

    with patch.object(service.users, "delete_by_user_id") as mock_delete:
        service.unlink("123456")

    mock_delete.assert_called_once_with(user_id)


def test_unlink_swallows_auth_delete_failure():
    user_id = uuid4()
    db = MagicMock(spec=Session)
    db.execute.return_value.first.return_value = (user_id,)
    service = KakaoWebhookService(db)

    with patch.object(
        service.users,
        "delete_by_user_id",
        side_effect=AppError(ErrorCode.EXTERNAL_API_ERROR, "gone", status_code=502),
    ):
        service.unlink("123456")
