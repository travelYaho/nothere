"""일정 CRUD HTTP 엔드포인트. 모든 작업은 현재 사용자 소유 행만 대상으로 한다."""
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from app.schemas.user import CurrentUser
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=ScheduleListResponse)
def list_schedules(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleListResponse:
    return ScheduleService(db).list_schedules(current_user)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    return ScheduleService(db).create_schedule(current_user, payload)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    return ScheduleService(db).get_schedule(current_user, schedule_id)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: UUID,
    payload: ScheduleUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleResponse:
    return ScheduleService(db).update_schedule(current_user, schedule_id, payload)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    ScheduleService(db).delete_schedule(current_user, schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
