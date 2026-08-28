"""사용자 조회/수정 API 와 인증 의존성에서 쓰는 스키마를 정의한다."""
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class UserResponse(APIModel):
    """프론트에 반환하는 기본 사용자 프로필 응답."""
    id: UUID
    email: str
    nickname: str
    profile_image_url: str | None = None


class UserUpdateRequest(APIModel):
    """부분 수정 가능한 사용자 입력값."""
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    profile_image_url: str | None = None


class CurrentUser(APIModel):
    """JWT 검증 후 내부 로직에서 재사용하는 현재 사용자 정보."""
    id: UUID
    email: str
    nickname: str
    profile_image_url: str | None = None
