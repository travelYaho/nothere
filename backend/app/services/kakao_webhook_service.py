"""카카오가 서비스 외부 연결 해제를 알려줄 때 회원 정보를 정리한다."""
from __future__ import annotations

import hmac
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.services.user_service import UserService

logger = logging.getLogger("yeogimalgo")

_ADMIN_PREFIX = "KakaoAK "


def kakao_admin_authorized(authorization: str | None) -> bool:
    """연결 해제 웹훅의 Authorization: KakaoAK {대표 어드민 키} 를 검증한다."""
    expected = settings.KAKAO_ADMIN_KEY.strip()
    if not expected or not authorization:
        return False
    if not authorization.startswith(_ADMIN_PREFIX):
        return False
    provided = authorization[len(_ADMIN_PREFIX) :].strip()
    try:
        return hmac.compare_digest(provided, expected)
    except Exception:
        return False


class KakaoWebhookService:
    """카카오 회원번호(provider_id)로 Supabase 사용자를 찾아 탈퇴 처리한다."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserService(db)

    def find_user_id(self, kakao_user_id: str) -> UUID | None:
        """auth.identities 에서 카카오 provider_id 에 해당하는 Auth 유저를 찾는다."""
        row = self.db.execute(
            text(
                """
                SELECT user_id
                FROM auth.identities
                WHERE provider = 'kakao'
                  AND provider_id = :kakao_id
                LIMIT 1
                """
            ),
            {"kakao_id": str(kakao_user_id)},
        ).first()
        if row is None:
            return None
        return UUID(str(row[0]))

    def unlink(self, kakao_user_id: str) -> None:
        """카카오 연결 해제 시 서비스 회원 데이터를 삭제한다. 대상이 없어도 예외를 내지 않는다."""
        user_id = self.find_user_id(kakao_user_id)
        if user_id is None:
            logger.info("kakao unlink: no auth user for provider_id")
            return
        try:
            self.users.delete_by_user_id(user_id)
        except AppError as exc:
            if exc.code == ErrorCode.EXTERNAL_API_ERROR:
                logger.warning("kakao unlink: auth user already gone or delete failed")
                return
            raise
