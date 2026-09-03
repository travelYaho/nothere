"""STEP2 조건입력 완료(여행 생성) 엔드포인트를 정의한다."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.trip import TripCreateRequest, TripCreateResponse
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
