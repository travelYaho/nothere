"""STEP3 장소 검색/추가/삭제/순서변경/방문시간수정 엔드포인트를 정의한다."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.place import (
    CustomPlaceAddRequest,
    CustomPlaceAddResponse,
    PlaceSearchResponse,
    TripPlaceAddRequest,
    TripPlaceAddResponse,
    TripPlaceOrderUpdateRequest,
    TripPlaceOrderUpdateResponse,
    TripPlaceVisitUpdateRequest,
    TripPlaceVisitUpdateResponse,
)
from app.schemas.user import CurrentUser
from app.services.place_service import PlaceService

router = APIRouter(tags=["places"])


@router.get("/places/search", response_model=ApiResponse[PlaceSearchResponse])
def search_places(
    keyword: str,
    region_id: int | None = Query(default=None, alias="regionId"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PlaceSearchResponse]:
    """TourAPI 기반으로 장소를 검색하고, 결과를 내부 Place 로 get-or-create 한다."""
    return ApiResponse(data=PlaceService(db).search_places(keyword, region_id))


@router.post(
    "/trips/{trip_id}/places",
    response_model=ApiResponse[TripPlaceAddResponse],
    status_code=201,
)
def add_trip_place(
    trip_id: UUID,
    payload: TripPlaceAddRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[TripPlaceAddResponse]:
    """검색된 장소를 여행 일정에 추가한다. 중복 등록은 409로 거절한다."""
    return ApiResponse(data=PlaceService(db).add_place_to_trip(current_user, trip_id, payload))


@router.post(
    "/trips/{trip_id}/places/custom",
    response_model=ApiResponse[CustomPlaceAddResponse],
    status_code=201,
)
def add_custom_trip_place(
    trip_id: UUID,
    payload: CustomPlaceAddRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[CustomPlaceAddResponse]:
    """검색 결과에 없는 장소를 이름/분류/주소로 직접 등록해 일정에 추가한다."""
    return ApiResponse(data=PlaceService(db).add_custom_place_to_trip(current_user, trip_id, payload))


@router.delete("/trip-places/{trip_place_id}", status_code=204)
def remove_trip_place(
    trip_place_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """등록된 장소를 삭제한다. 최소 장소 수 미달이면 409로 거절한다."""
    PlaceService(db).remove_place_from_trip(current_user, trip_place_id)


@router.patch("/trips/{trip_id}/places/order", response_model=ApiResponse[TripPlaceOrderUpdateResponse])
def reorder_trip_places(
    trip_id: UUID,
    payload: TripPlaceOrderUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[TripPlaceOrderUpdateResponse]:
    """장소 방문 순서를 일괄 변경한다. 항상 재분석이 필요해진다."""
    return ApiResponse(data=PlaceService(db).reorder_places(current_user, trip_id, payload))


@router.patch("/trip-places/{trip_place_id}", response_model=ApiResponse[TripPlaceVisitUpdateResponse])
def update_trip_place_visit(
    trip_place_id: UUID,
    payload: TripPlaceVisitUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[TripPlaceVisitUpdateResponse]:
    """방문시간/체류시간/고정여부를 부분 수정한다."""
    return ApiResponse(data=PlaceService(db).update_trip_place_visit(current_user, trip_place_id, payload))
