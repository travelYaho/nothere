"""일정·장소 API 요청/응답 스키마."""
from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class PlaceCreate(APIModel):
    """일정 생성/수정 시 함께 넣는 장소 입력."""
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str | None = None
    order_index: int = Field(default=0, ge=0)
    stay_minutes: int | None = Field(default=None, ge=0)
    external_id: str | None = Field(default=None, max_length=100)


class PlaceResponse(APIModel):
    """장소 응답."""
    id: UUID
    name: str
    latitude: float
    longitude: float
    address: str | None = None
    order_index: int
    stay_minutes: int | None = None
    external_id: str | None = None


class ScheduleCreateRequest(APIModel):
    """일정 생성 요청."""
    title: str = Field(min_length=1, max_length=200)
    travel_date: date | None = None
    region_code: str | None = Field(default=None, max_length=50)
    status: str = Field(default="DRAFT", max_length=20)
    places: list[PlaceCreate] = Field(default_factory=list)


class ScheduleUpdateRequest(APIModel):
    """일정 부분 수정. places 가 오면 기존 장소를 통째로 교체한다."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    travel_date: date | None = None
    region_code: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=20)
    places: list[PlaceCreate] | None = None


class ScheduleResponse(APIModel):
    """일정 상세 응답(장소 포함)."""
    id: UUID
    title: str
    travel_date: date | None = None
    region_code: str | None = None
    status: str
    places: list[PlaceResponse] = Field(default_factory=list)


class ScheduleListResponse(APIModel):
    """일정 목록 응답."""
    items: list[ScheduleResponse]
