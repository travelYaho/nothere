"""보호 API 에서 공통으로 쓰는 JWT 인증 의존성 모듈이다.

Bearer 토큰을 검증한 뒤, 서비스 프로필 테이블에서 현재 사용자 정보를 다시 조회한다.

- get_current_user: 보호 API 전반. 토큰 서명을 Supabase JWKS 공개키로 로컬 검증한다.
  매 요청 Supabase Auth(/auth/v1/user)를 네트워크로 부르면 요청마다 수백 ms 가 붙어서다.
- get_auth_user: OAuth 첫 로그인(ensure-profile)처럼 identities 등 JWT 에 없는 정보가
  필요한 곳에서만 쓴다. Supabase Auth 에 직접 물어본다.
"""
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.core.supabase import get_anon_client
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser

http_bearer = HTTPBearer(auto_error=False)

# 서버와 Supabase Auth 시계가 조금만 어긋나도 막 발급된 토큰의 iat 가 "미래"로 보여
# 거부되지 않도록 허용 오차를 둔다.
_JWT_LEEWAY_SECONDS = 30


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


def _bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or not credentials.credentials:
        raise AppError(
            ErrorCode.AUTH_TOKEN_MISSING,
            "인증 토큰이 없습니다.",
            status_code=401,
        )
    return credentials.credentials


def _invalid_token() -> AppError:
    return AppError(
        ErrorCode.AUTH_TOKEN_INVALID,
        "인증 토큰이 유효하지 않습니다.",
        status_code=401,
    )


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    """Supabase 프로젝트의 JWT 서명 공개키(JWKS). 키 세트는 lifespan 동안 캐시된다."""
    base = settings.SUPABASE_URL.rstrip("/")
    return jwt.PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json", lifespan=600, timeout=5)


def _verify_locally(token: str) -> AuthUser | None:
    """비대칭 키(ES256/RS256)로 서명된 토큰을 JWKS 로 검증한다.

    레거시 HS256 토큰이거나 JWKS 조회/키 매칭이 안 되면 None 을 돌려 호출부가
    Supabase Auth 네트워크 검증으로 넘어가게 한다.
    """
    try:
        alg = jwt.get_unverified_header(token).get("alg")
    except jwt.InvalidTokenError as exc:
        raise _invalid_token() from exc
    if alg not in ("ES256", "RS256"):
        return None

    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
    except jwt.PyJWKClientError:
        return None

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience="authenticated",
            leeway=_JWT_LEEWAY_SECONDS,
            issuer=f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError(
            ErrorCode.AUTH_TOKEN_EXPIRED,
            "인증 토큰이 만료되었습니다.",
            status_code=401,
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise _invalid_token() from exc

    try:
        user_id = UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise _invalid_token() from exc
    return AuthUser(
        id=user_id,
        email=claims.get("email") or "",
        user_metadata=_as_dict(claims.get("user_metadata")),
    )


def _verify_with_supabase(token: str) -> AuthUser:
    """Supabase Auth 에 토큰 검증을 위임하고 identities 까지 포함한 사용자 정보를 받는다."""
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
        raise _invalid_token() from exc

    auth_user = response.user
    if auth_user is None or not auth_user.id:
        raise _invalid_token()

    return AuthUser(
        id=UUID(str(auth_user.id)),
        email=auth_user.email or "",
        user_metadata=_as_dict(getattr(auth_user, "user_metadata", None)),
        identities=list(getattr(auth_user, "identities", None) or []),
    )


def get_auth_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> AuthUser:
    """Supabase Auth 로 토큰을 검증하고 identities 를 포함한 Auth 사용자를 반환한다."""
    return _verify_with_supabase(_bearer_token(credentials))


def get_token_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
) -> AuthUser:
    """JWT 를 로컬에서 검증한다(불가하면 Supabase Auth 로 폴백). identities 는 비어 있다."""
    token = _bearer_token(credentials)
    return _verify_locally(token) or _verify_with_supabase(token)


def get_current_user(
    auth_user: AuthUser = Depends(get_token_user),
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
