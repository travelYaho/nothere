"""보호 API 에서 공통으로 쓰는 JWT 인증 의존성 모듈이다.

Bearer 토큰을 Supabase Auth 로 검증한 뒤,
서비스 프로필 테이블에서 현재 사용자 정보를 다시 조회한다.
"""
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.core.supabase import get_anon_client
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser

http_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Authorization 헤더를 검사해 현재 로그인 사용자 정보를 반환한다."""
    if credentials is None or not credentials.credentials:
        raise AppError(
            ErrorCode.AUTH_TOKEN_MISSING,
            "인증 토큰이 없습니다.",
            status_code=401,
        )

    token = credentials.credentials
    try:
        # publishable key 클라이언트 로 Supabase Auth 에 토큰 유효성을 위임한다.
        response = get_anon_client().auth.get_user(token)
    except Exception as exc:
        message = str(exc).lower()
        if "expired" in message:
            raise AppError(
                ErrorCode.AUTH_TOKEN_EXPIRED,
                "인증 토큰이 만료되었습니다.",
                status_code=401,
            ) from exc
        raise AppError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "인증 토큰이 유효하지 않습니다.",
            status_code=401,
        ) from exc

    auth_user = response.user
    if auth_user is None or not auth_user.id:
        raise AppError(
            ErrorCode.AUTH_TOKEN_INVALID,
            "인증 토큰이 유효하지 않습니다.",
            status_code=401,
        )

    user_id = UUID(str(auth_user.id))
    # auth.users 와 별개로, 서비스에서 쓰는 profile 행이 실제로 존재하는지 확인한다.
    profile = UserRepository(db).get_by_id(user_id)
    if profile is None:
        raise AppError(
            ErrorCode.USER_NOT_FOUND,
            "사용자를 찾을 수 없습니다.",
            status_code=404,
        )

    return CurrentUser(
        id=profile.id,
        email=auth_user.email or "",
        nickname=profile.nickname,
        profile_image_url=profile.profile_image_url,
    )
