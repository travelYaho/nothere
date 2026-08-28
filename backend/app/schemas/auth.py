"""인증 API 의 요청/응답 JSON 스키마를 정의한다."""
from pydantic import EmailStr, Field

from app.schemas.common import APIModel
from app.schemas.user import UserResponse


class SignupRequest(APIModel):
    """회원가입에 필요한 이메일, 비밀번호, 닉네임 입력값."""
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    nickname: str = Field(min_length=1, max_length=50)


class SignupResponse(APIModel):
    """회원가입 응답. 이메일 확인 설정에 따라 토큰이 없을 수도 있다."""
    user: UserResponse
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str | None = None
