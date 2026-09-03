"""STEP2 조건입력(여행 생성) API 의 요청/응답 스키마를 정의한다."""
from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class TripCreateRequest(APIModel):
    """STEP2 폼 제출 요청. preferredExperienceTagIds 의 개수(2~3개) 검증은
    서비스 계층에서 처리해 전용 에러 코드(invalid_preferred_experience_count)를
    반환한다 — pydantic 필드 제약을 걸면 일반 VALIDATION_ERROR(422)로 뭉개진다.
    """
    title: str | None = None
    travel_date: date
    region_id: int
    companion_type: str | None = None
    transport_mode: str | None = None
    extra_time_limit_minutes: int | None = None
    preferred_experience_tag_ids: list[int] = Field(default_factory=list)


class TripCreateResponse(APIModel):
    """POST /trips 201 응답."""
    trip_id: UUID
    title: str
    status: str
    current_step: int
    created_at: datetime
