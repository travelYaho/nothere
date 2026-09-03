"""STEP2 조건입력·수정·삭제(여행 생성/수정/삭제) 엔드포인트를 정의한다."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.trip import (
    TripConditionsUpdateRequest,
    TripConditionsUpdateResponse,
    TripCreateRequest,
    TripCreateResponse,
)
from app.schemas.user import CurrentUser
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=ApiResponse[TripCreateResponse], status_code=201)
def create_trip(
    payload: TripCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[TripCreateResponse]:
    """STEP2 폼 제출 시 여행 일정을 생성하고 STEP3 진입 정보를 반환한다."""
    return ApiResponse(data=TripService(db).create_trip(current_user, payload))


@router.patch("/{trip_id}/conditions", response_model=ApiResponse[TripConditionsUpdateResponse])
def update_trip_conditions(
    trip_id: UUID,
    payload: TripConditionsUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[TripConditionsUpdateResponse]:
    """여행 날짜/지역/이동수단/허용시간/선호경험을 부분 수정한다."""
    return ApiResponse(data=TripService(db).update_conditions(current_user, trip_id, payload))


@router.delete("/{trip_id}", status_code=204)
def delete_trip(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """여행 일정을 하드 삭제한다(TripPlace 등은 FK cascade로 함께 삭제)."""
    TripService(db).delete_trip(current_user, trip_id)
