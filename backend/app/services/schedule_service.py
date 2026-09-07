"""일정 CRUD — 구 schedules 스키마 폐기 후 trip 전환 대기.

현재 통합 스키마에는 schedules / schedule_places 가 없다.
엔드포인트는 유지하되 호출 시 명확한 오류를 반환한다.
"""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from app.schemas.user import CurrentUser

_MSG = "schedules API는 통합 스키마(trip)로 이전 중입니다. /api/trips 를 사용하세요."


class ScheduleService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_schedules(self, current_user: CurrentUser) -> ScheduleListResponse:
        raise AppError(ErrorCode.INVALID_REQUEST, _MSG, 501)

    def get_schedule(self, current_user: CurrentUser, schedule_id: UUID) -> ScheduleResponse:
        raise AppError(ErrorCode.INVALID_REQUEST, _MSG, 501)

    def create_schedule(
        self,
        current_user: CurrentUser,
        payload: ScheduleCreateRequest,
    ) -> ScheduleResponse:
        raise AppError(ErrorCode.INVALID_REQUEST, _MSG, 501)

    def update_schedule(
        self,
        current_user: CurrentUser,
        schedule_id: UUID,
        payload: ScheduleUpdateRequest,
    ) -> ScheduleResponse:
        raise AppError(ErrorCode.INVALID_REQUEST, _MSG, 501)

    def delete_schedule(self, current_user: CurrentUser, schedule_id: UUID) -> None:
        raise AppError(ErrorCode.INVALID_REQUEST, _MSG, 501)
