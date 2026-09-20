"""보호 API 에서 공통으로 쓰는 JWT 인증 의존성 모듈이다.

Bearer 토큰을 Supabase Auth 로 검증한 뒤,
서비스 프로필 테이블에서 현재 사용자 정보를 다시 조회한다.
OAuth 첫 로그인처럼 profile 이 아직 없는 경우는 get_auth_user 만 쓴다.
"""
from dataclasses import dataclass, field
from typing import Any
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


@dataclass(frozen=True)
class AuthUser:
    """JWT 검증만 통과한 Auth 사용자. 서비스 profile 존재 여부는 보장하지 않는다."""

    id: UUID
    email: str
    user_metadata: dict[str, Any] = field(default_factory=dict)
    identities: list[Any] = field(default_factory=list)


def _as_dict(value: Any) -> dict[str, Any]:
    """SDK 객체/딕셔너리를 metadata 조회용 dict 로 맞춘다."""
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    return {}


def get_auth_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> AuthUser:
    """Authorization 헤더의 JWT 만 검사하고 Auth 사용자를 반환한다."""
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

    return AuthUser(
        id=UUID(str(auth_user.id)),
        email=auth_user.email or "",
        user_metadata=_as_dict(getattr(auth_user, "user_metadata", None)),
        identities=list(getattr(auth_user, "identities", None) or []),
    )


def get_current_user(
    auth_user: AuthUser = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """JWT 사용자를 서비스 profile 과 연결해 현재 로그인 사용자 정보를 반환한다."""
    # auth.users 와 별개로, 서비스에서 쓰는 profile 행이 실제로 존재하는지 확인한다.
    profile = UserRepository(db).get_by_id(auth_user.id)
    if profile is None:
        raise AppError(
            ErrorCode.USER_NOT_FOUND,
            "사용자를 찾을 수 없습니다.",
            status_code=404,
        )

    return CurrentUser(
        id=profile.id,
        email=auth_user.email,
        nickname=profile.nickname,
        profile_image_url=profile.profile_image_url,
    )
