"""방문 목적 태그 조회/저장 엔드포인트를 정의한다."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.purpose import PurposeGetResponse, PurposePutRequest, PurposePutResponse
from app.schemas.user import CurrentUser
from app.services.purpose_service import PurposeService

router = APIRouter(tags=["purpose"])


@router.get("/trip-places/{trip_place_id}/purpose", response_model=ApiResponse[PurposeGetResponse])
def get_trip_place_purpose(
    trip_place_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PurposeGetResponse]:
    """저장된 방문 목적 태그를 조회한다."""
    return ApiResponse(data=PurposeService(db).get_purpose(current_user, trip_place_id))


@router.put("/trip-places/{trip_place_id}/purpose", response_model=ApiResponse[PurposePutResponse])
def put_trip_place_purpose(
    trip_place_id: UUID,
    payload: PurposePutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[PurposePutResponse]:
    """방문 목적 태그를 다중선택 값으로 전체 교체 저장한다."""
    return ApiResponse(data=PurposeService(db).replace_purpose(current_user, trip_place_id, payload))
