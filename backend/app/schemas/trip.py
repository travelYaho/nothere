"""일정(trip) 목록·상세 API 요청/응답 스키마."""
from datetime import date, datetime, time
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class TripPlaceItem(APIModel):
    """일정 상세에 포함하는 장소 한 줄."""
    id: UUID
    place_id: UUID
    name: str
    position: int
    visit_time: time | None = None
    stay_minutes: int | None = None
    resolution_status: str


class TripListItem(APIModel):
    """일정 목록 카드용 요약."""
    id: UUID
    title: str
    travel_date: date | None = None
    status: str
    current_step: int | None = None
    place_count: int = 0
    created_at: datetime


class TripListResponse(APIModel):
    """내 일정 목록."""
    items: list[TripListItem] = Field(default_factory=list)


class TripDetailResponse(APIModel):
    """일정 상세(이어서 진행)."""
    id: UUID
    title: str
    travel_date: date | None = None
    status: str
    current_step: int | None = None
    region_id: int | None = None
    companion_type: str | None = None
    transport_mode: str | None = None
    extra_time_limit_minutes: int | None = None
    places: list[TripPlaceItem] = Field(default_factory=list)
    created_at: datetime
    confirmed_at: datetime | None = None
