"""STEP2 조건입력(여행 생성) 및 일정 상세조회 API 의 요청/응답 스키마를 정의한다."""
from datetime import date, datetime, time
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


class TripConditionsUpdateRequest(APIModel):
    """PATCH /trips/{tripId}/conditions 부분 수정 요청.

    전부 Optional 이며, 서비스 계층에서 `model_dump(exclude_unset=True)` 로
    실제 요청에 포함된 필드만 골라 반영한다(값을 null 로 지우는 것과 필드
    자체를 안 보낸 것을 구분하기 위해 기본값 None 대신 unset 여부를 본다).
    """
    title: str | None = None
    travel_date: date | None = None
    region_id: int | None = None
    companion_type: str | None = None
    transport_mode: str | None = None
    extra_time_limit_minutes: int | None = None
    preferred_experience_tag_ids: list[int] | None = None


class TripConditionsUpdateResponse(APIModel):
    """PATCH /trips/{tripId}/conditions 200 응답."""
    trip_id: UUID
    needs_reanalysis: bool
    warnings: list[str]
    updated_at: datetime


class TripPlaceDetail(APIModel):
    """GET /trips/{tripId} 응답에 포함되는 등록된 장소 한 건.

    STEP3 리스트 카드(Figma node 48:2979/48:3158)엔 이름/방문시간/체류시간만
    보이므로 category 는 포함하지 않는다(TourAPI 소스 장소는 애초에 category 를
    저장하지 않기도 한다 — Place 모델 주석 참고).
    """
    trip_place_id: UUID
    place_id: UUID
    name: str
    visit_order: int
    visit_time: time | None = None
    duration_minutes: int | None = None
    is_fixed: bool


class TripDetailResponse(APIModel):
    """GET /trips/{tripId} 200 응답 — 일정 상세(이어서 진행)."""
    trip_id: UUID
    title: str
    travel_date: date | None
    region_id: int
    region_name: str
    companion_type: str | None
    transport_mode: str | None
    extra_time_limit_minutes: int | None
    status: str
    current_step: int
    needs_reanalysis: bool
    preferred_experience_tag_ids: list[int]
    places: list[TripPlaceDetail]
