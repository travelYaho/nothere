"""인증 API 의 요청/응답 JSON 스키마를 정의한다."""
from pydantic import EmailStr, Field

from app.schemas.common import APIModel
from app.schemas.user import UserResponse


class SignupRequest(APIModel):
    """회원가입에 필요한 이메일, 비밀번호, 닉네임 입력값."""
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    nickname: str = Field(min_length=1, max_length=50)


class LoginRequest(APIModel):
    """이메일·비밀번호 로그인 입력값."""
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class RefreshRequest(APIModel):
    """액세스 토큰 재발급에 쓰는 리프레시 토큰."""
    refresh_token: str = Field(min_length=1)


class PasswordResetRequest(APIModel):
    """비밀번호 재설정 메일 요청."""
    email: EmailStr


class AuthSessionResponse(APIModel):
    """로그인/회원가입 공통 세션 응답. 이메일 확인 설정에 따라 토큰이 없을 수도 있다."""
    user: UserResponse
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None


class SignupResponse(AuthSessionResponse):
    """회원가입 응답. AuthSessionResponse 와 동일한 형태."""


class TokenResponse(APIModel):
    """토큰 재발급 응답."""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class MessageResponse(APIModel):
    """단순 안내 메시지."""
    message: str
