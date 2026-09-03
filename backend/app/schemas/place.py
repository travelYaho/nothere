"""STEP3 장소 검색/추가/삭제/순서변경/방문시간수정 API 의 요청/응답 스키마를 정의한다."""
from datetime import datetime, time
from uuid import UUID

from app.schemas.common import APIModel


class PlaceSearchItem(APIModel):
    """TourAPI 검색 결과 한 건 — placeId 는 우리 내부 Place.id(UUID)다."""
    place_id: UUID
    name: str
    category: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class PlaceSearchResponse(APIModel):
    """GET /places/search 응답 전체 묶음."""
    places: list[PlaceSearchItem]


class TripPlaceAddRequest(APIModel):
    """POST /trips/{tripId}/places 요청."""
    place_id: UUID


class TripPlaceAddResponse(APIModel):
    """POST /trips/{tripId}/places 201 응답."""
    trip_place_id: UUID
    trip_id: UUID
    place_id: UUID
    visit_order: int
    is_fixed: bool


class TripPlaceOrderItem(APIModel):
    """PATCH /trips/{tripId}/places/order 요청의 개별 항목."""
    trip_place_id: UUID
    visit_order: int


class TripPlaceOrderUpdateRequest(APIModel):
    """PATCH /trips/{tripId}/places/order 요청."""
    order: list[TripPlaceOrderItem]


class TripPlaceOrderUpdateResponse(APIModel):
    """PATCH /trips/{tripId}/places/order 200 응답. 순서변경은 항상 재분석이 필요하다."""
    trip_id: UUID
    needs_reanalysis: bool
    updated_at: datetime


class TripPlaceVisitUpdateRequest(APIModel):
    """PATCH /trip-places/{tripPlaceId} 부분 수정 요청."""
    visit_time: time | None = None
    duration_minutes: int | None = None
    is_fixed: bool | None = None


class TripPlaceVisitUpdateResponse(APIModel):
    """PATCH /trip-places/{tripPlaceId} 200 응답.

    방문시간·체류시간·고정여부 수정은 needsReanalysis 를 바꾸지 않는다
    (visitTime/durationMinutes 는 명세서에 명시, isFixed 의 영향 여부는
    명세서 원문에서도 "미정"이라고 남겨둔 항목이라 보수적으로 동일하게
    처리했다 — 팀 확정 필요).
    """
    trip_place_id: UUID
    visit_time: time | None = None
    duration_minutes: int | None = None
    is_fixed: bool
    needs_reanalysis: bool
    updated_at: datetime
