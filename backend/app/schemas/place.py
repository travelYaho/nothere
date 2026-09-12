"""STEP3 장소 검색/추가/삭제/순서변경/방문시간수정 API 의 요청/응답 스키마를 정의한다."""
import re
from datetime import datetime, time
from uuid import UUID

from pydantic import field_validator

from app.schemas.common import APIModel

# 시/도, 시/군/구, 도로명+번지 정도의 최소 구성 요소를 갖췄는지만 확인한다.
# 프론트(CustomPlaceForm.tsx)는 다음 우편번호 검색으로 실제 주소만 선택하게
# 강제하므로 이 휴리스틱이 필요 없지만, 여기서는 그 UI를 거치지 않은 직접
# API 호출까지 막기 위한 최소한의 방어선으로 유지한다.
_ADDRESS_MIN_SEGMENTS = 3


def _is_complete_address(value: str) -> bool:
    segments = [s for s in re.split(r"\s+", value.strip()) if s]
    if len(segments) < _ADDRESS_MIN_SEGMENTS:
        return False
    return any(re.search(r"\d", s) for s in segments)


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
    visit_time: time | None = None


class TripPlaceAddResponse(APIModel):
    """POST /trips/{tripId}/places 201 응답."""
    trip_place_id: UUID
    trip_id: UUID
    place_id: UUID
    visit_order: int
    visit_time: time | None
    is_fixed: bool


class CustomPlaceAddRequest(APIModel):
    """POST /trips/{tripId}/places/custom 요청 — 검색 결과에 없는 장소를 직접 등록한다.

    분류(경험태그) 선택은 받지 않는다 — 어차피 커스텀 장소는
    is_recommendable=False 라 추천 후보 조회에 안 걸려서 저장해도 쓰이지 않았고,
    STEP3 완료 직후 "방문 목적" 화면에서 같은 경험태그 목록을 다시 물어봐서
    사용자 입장에선 같은 선택을 두 번 하는 것으로 보였다(TripPurposeForm.tsx).
    """
    name: str
    address: str
    visit_time: time | None = None

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        if not _is_complete_address(value):
            raise ValueError("시/군/구, 도로명, 번지까지 포함한 전체 주소를 입력해야 합니다.")
        return value


class CustomPlaceAddResponse(APIModel):
    """POST /trips/{tripId}/places/custom 201 응답."""
    trip_place_id: UUID
    trip_id: UUID
    place_id: UUID
    visit_order: int
    visit_time: time | None
    is_fixed: bool
    name: str


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
