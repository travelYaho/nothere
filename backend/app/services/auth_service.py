"""Supabase Auth 회원가입과 서비스 profile 생성을 묶는 인증 서비스이다.

로그인/로그아웃/토큰 재발급은 프론트엔드가 Supabase Auth 를 직접 사용한다.
서비스 전용 사용자 정보는 profile 테이블에서 관리한다.
"""
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.core.supabase import delete_auth_user, new_anon_client
from app.repositories.user_repository import UserRepository
from app.schemas.auth import SignupRequest, SignupResponse
from app.schemas.user import UserResponse


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


def _to_user_response(user_id: UUID, email: str, nickname: str, profile_image_url: str | None) -> UserResponse:
    """Supabase/Auth + profile 정보를 프론트 응답 스키마로 합친다."""
    return UserResponse(
        id=user_id,
        email=email,
        nickname=nickname,
        profile_image_url=profile_image_url,
    )


class AuthService:
    """회원가입 라우터가 호출하는 Supabase Auth 연동 로직을 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

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
                # profile 저장 실패 시 auth.users orphan 방지를 위해 Auth 유저를 롤백한다.
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
        user = _to_user_response(
            profile.id,
            auth_user.email or payload.email,
            profile.nickname,
            profile.profile_image_url,
        )
        if session is None:
            return SignupResponse(user=user)

        return SignupResponse(
            user=user,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            token_type="bearer",
        )
