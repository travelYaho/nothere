"""홈 화면 응답 전용 스키마를 정의한다."""
from datetime import date
from uuid import UUID

from app.schemas.common import APIModel


class HomeUserResponse(APIModel):
    """홈 상단에 필요한 최소 사용자 정보."""
    id: UUID
    nickname: str


# [홈 범위] 홈 응답용 최소 일정 요약. 상세/장소는 /api/schedules 응답을 사용한다.
class ScheduleSummary(APIModel):
    """홈 카드에서 보여줄 최소 일정 정보만 담는다."""
    schedule_id: UUID
    title: str
    travel_date: date | None = None
    status: str


class HomeResponse(APIModel):
    """홈 화면 한 번 호출로 반환할 사용자 + 일정 요약 묶음."""
    user: HomeUserResponse
    draft_schedule: ScheduleSummary | None = None
    recent_schedules: list[ScheduleSummary]
