"""Supabase Auth 와 서비스 profile 생성을 묶는 인증 서비스이다.

로그인/로그아웃/토큰 재발급/비밀번호 재설정도 백엔드가 Auth API 를 감싼다.
서비스 전용 사용자 정보는 profile 테이블에서 관리한다.
"""
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.core.supabase import delete_auth_user, new_anon_client
from app.db.models.profile import Profile
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AuthSessionResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetRequest,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.schemas.user import UserResponse

SOCIAL_PROVIDERS = frozenset({"kakao", "google"})


def _auth_error_code(exc: Exception) -> str:
    """SDK 예외 객체에서 에러 코드를 최대한 안전하게 꺼낸다."""
    return str(getattr(exc, "code", "") or "").lower()


def _auth_error_text(exc: Exception) -> str:
    """SDK 예외 메시지를 소문자로 정규화해 분기 조건에 재사용한다."""
    return str(exc).lower()


def _map_signup_error(exc: Exception) -> AppError:
    """회원가입 예외를 서비스 공통 에러 코드로 변환한다."""
    code = _auth_error_code(exc)
    text = _auth_error_text(exc)
    if code in {"user_already_exists", "email_exists"} or "already" in text or "registered" in text:
        return AppError(
            ErrorCode.AUTH_EMAIL_ALREADY_EXISTS,
            "이미 가입된 이메일입니다.",
            status_code=409,
        )
    return AppError(
        ErrorCode.VALIDATION_ERROR,
        "회원가입에 실패했습니다.",
        status_code=400,
    )


def _map_login_error(exc: Exception) -> AppError:
    """로그인 예외를 자격 증명 오류로 변환한다."""
    code = _auth_error_code(exc)
    text = _auth_error_text(exc)
    if (
        code in {"invalid_credentials", "invalid_grant", "email_not_confirmed"}
        or "invalid login" in text
        or "invalid" in text
        or "credentials" in text
    ):
        return AppError(
            ErrorCode.AUTH_INVALID_CREDENTIALS,
            "이메일 또는 비밀번호가 올바르지 않습니다.",
            status_code=401,
        )
    return AppError(
        ErrorCode.AUTH_INVALID_CREDENTIALS,
        "로그인에 실패했습니다.",
        status_code=401,
    )


def _to_user_response(user_id: UUID, email: str, nickname: str, profile_image_url: str | None) -> UserResponse:
    """Supabase/Auth + profile 정보를 프론트 응답 스키마로 합친다."""
    return UserResponse(
        id=user_id,
        email=email,
        nickname=nickname,
        profile_image_url=profile_image_url,
    )


def _nickname_from_auth(email: str, user_metadata: object) -> str:
    """소셜/로그인 시 profile 이 없을 때 쓸 닉네임을 Auth 메타데이터에서 고른다."""
    metadata = user_metadata if isinstance(user_metadata, dict) else {}
    raw = (
        metadata.get("nickname")
        or metadata.get("full_name")
        or metadata.get("name")
        or (email.split("@")[0] if email else "")
        or "사용자"
    )
    return str(raw).strip()[:50] or "사용자"


class AuthService:
    """인증 라우터가 호출하는 Supabase Auth 연동 로직을 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def _ensure_profile(self, user_id: UUID, email: str, user_metadata: object) -> Profile:
        """auth.users 와 같은 UUID 의 profile 이 없으면 생성한다."""
        profile = self.users.get_by_id(user_id)
        if profile is not None:
            return profile
        nickname = _nickname_from_auth(email, user_metadata)
        try:
            return self.users.create(user_id=user_id, nickname=nickname)
        except SQLAlchemyError as exc:
            raise AppError(
                ErrorCode.DB_ERROR,
                "사용자 프로필을 저장하는 중 오류가 발생했습니다.",
                status_code=500,
            ) from exc

    def _session_response(
        self,
        profile: Profile,
        email: str,
        access_token: str | None,
        refresh_token: str | None,
        as_signup: bool = False,
    ) -> AuthSessionResponse:
        user = _to_user_response(profile.id, email, profile.nickname, profile.profile_image_url)
        cls = SignupResponse if as_signup else AuthSessionResponse
        if not access_token:
            return cls(user=user)
        return cls(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    def signup(self, payload: SignupRequest) -> SignupResponse:
        """Supabase Auth 회원가입 후 같은 UUID 로 profile 을 생성한다."""
        client = new_anon_client()
        try:
            result = client.auth.sign_up(
                {
                    "email": payload.email,
                    "password": payload.password,
                    "options": {"data": {"nickname": payload.nickname}},
                }
            )
        except Exception as exc:
            raise _map_signup_error(exc) from exc

        auth_user = result.user
        if auth_user is None or not auth_user.id:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "회원가입에 실패했습니다.",
                status_code=400,
            )

        identities = getattr(auth_user, "identities", None)
        if identities is not None and len(identities) == 0:
            raise AppError(
                ErrorCode.AUTH_EMAIL_ALREADY_EXISTS,
                "이미 가입된 이메일입니다.",
                status_code=409,
            )

        user_id = UUID(str(auth_user.id))
        profile = self.users.get_by_id(user_id)
        if profile is None:
            try:
                profile = self.users.create(user_id=user_id, nickname=payload.nickname)
            except SQLAlchemyError as exc:
                try:
                    delete_auth_user(user_id)
                except Exception:
                    pass
                raise AppError(
                    ErrorCode.DB_ERROR,
                    "사용자 프로필을 저장하는 중 오류가 발생했습니다.",
                    status_code=500,
                ) from exc

        session = result.session
        return self._session_response(
            profile,
            auth_user.email or payload.email,
            session.access_token if session else None,
            session.refresh_token if session else None,
            as_signup=True,
        )

    def login(self, payload: LoginRequest) -> AuthSessionResponse:
        """이메일·비밀번호로 로그인하고 profile 이 없으면 생성한다."""
        client = new_anon_client()
        try:
            result = client.auth.sign_in_with_password(
                {"email": payload.email, "password": payload.password}
            )
        except Exception as exc:
            raise _map_login_error(exc) from exc

        auth_user = result.user
        session = result.session
        if auth_user is None or not auth_user.id or session is None:
            raise AppError(
                ErrorCode.AUTH_INVALID_CREDENTIALS,
                "이메일 또는 비밀번호가 올바르지 않습니다.",
                status_code=401,
            )

        user_id = UUID(str(auth_user.id))
        email = auth_user.email or payload.email
        metadata = getattr(auth_user, "user_metadata", None)
        profile = self._ensure_profile(user_id, email, metadata)
        return self._session_response(
            profile,
            email,
            session.access_token,
            session.refresh_token,
        )

    def refresh(self, payload: RefreshRequest) -> TokenResponse:
        """리프레시 토큰으로 액세스 토큰을 재발급한다."""
        client = new_anon_client()
        try:
            result = client.auth.refresh_session(payload.refresh_token)
        except Exception as exc:
            raise AppError(
                ErrorCode.AUTH_TOKEN_INVALID,
                "토큰을 갱신할 수 없습니다.",
                status_code=401,
            ) from exc

        session = result.session
        if session is None or not session.access_token:
            raise AppError(
                ErrorCode.AUTH_TOKEN_INVALID,
                "토큰을 갱신할 수 없습니다.",
                status_code=401,
            )
        return TokenResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            token_type="bearer",
        )

    def logout(self, access_token: str) -> None:
        """Supabase 세션을 만료시킨다. 실패해도 클라이언트 토큰 삭제를 막지 않는다."""
        client = new_anon_client()
        try:
            client.auth.set_session(access_token, access_token)
        except Exception:
            pass
        try:
            client.auth.sign_out()
        except Exception:
            pass

    def request_password_reset(self, payload: PasswordResetRequest) -> MessageResponse:
        """비밀번호 재설정 메일을 보낸다. 계정 존재 여부는 구분하지 않는다."""
        client = new_anon_client()
        redirect_to = f"{settings.FRONTEND_PUBLIC_ORIGIN.rstrip('/')}/login"
        try:
            client.auth.reset_password_for_email(
                payload.email,
                {"redirect_to": redirect_to},
            )
        except Exception:
            pass
        return MessageResponse(message="비밀번호 재설정 안내를 보냈습니다.")

    def social_login(self, provider: str) -> None:
        """소셜 로그인은 라우트만 열어 두고 실제 OAuth 는 아직 지원하지 않는다."""
        normalized = provider.strip().lower()
        if normalized not in SOCIAL_PROVIDERS:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "지원하지 않는 소셜 로그인입니다.",
                status_code=400,
            )
        raise AppError(
            ErrorCode.NOT_IMPLEMENTED,
            "소셜 로그인은 아직 지원하지 않습니다.",
            status_code=501,
        )
