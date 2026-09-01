"""일정 CRUD 비즈니스 로직. 소유자 검증은 repository 필터 + not-found 로 처리한다."""
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.db.models.schedule import Schedule, ScheduleStatus
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.schedule import (
    PlaceResponse,
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from app.schemas.user import CurrentUser

_ALLOWED_STATUSES = {s.value for s in ScheduleStatus}


def _to_response(schedule: Schedule) -> ScheduleResponse:
    places = sorted(schedule.places or [], key=lambda p: p.order_index)
    return ScheduleResponse(
        id=schedule.id,
        title=schedule.title,
        travel_date=schedule.travel_date,
        region_code=schedule.region_code,
        status=schedule.status,
        places=[
            PlaceResponse(
                id=p.id,
                name=p.name,
                latitude=p.latitude,
                longitude=p.longitude,
                address=p.address,
                order_index=p.order_index,
                stay_minutes=p.stay_minutes,
                external_id=p.external_id,
            )
            for p in places
        ],
    )


def _validate_status(status: str) -> str:
    if status not in _ALLOWED_STATUSES:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"status 값이 올바르지 않습니다. ({', '.join(sorted(_ALLOWED_STATUSES))})",
            status_code=422,
        )
    return status


class ScheduleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.schedules = ScheduleRepository(db)

    def list_schedules(self, current_user: CurrentUser) -> ScheduleListResponse:
        try:
            items = self.schedules.list_by_user(current_user.id)
        except SQLAlchemyError as exc:
            raise AppError(
                ErrorCode.DB_ERROR,
                "일정 목록을 조회하는 중 오류가 발생했습니다.",
                status_code=500,
            ) from exc
        return ScheduleListResponse(items=[_to_response(s) for s in items])

    def get_schedule(self, current_user: CurrentUser, schedule_id: UUID) -> ScheduleResponse:
        schedule = self.schedules.get_owned(schedule_id, current_user.id)
        if schedule is None:
            raise AppError(
                ErrorCode.SCHEDULE_NOT_FOUND,
                "일정을 찾을 수 없습니다.",
                status_code=404,
            )
        return _to_response(schedule)

    def create_schedule(
        self,
        current_user: CurrentUser,
        payload: ScheduleCreateRequest,
    ) -> ScheduleResponse:
        status = _validate_status(payload.status)
        try:
            schedule = self.schedules.create(
                user_id=current_user.id,
                title=payload.title,
                travel_date=payload.travel_date,
                region_code=payload.region_code,
                status=status,
                places=payload.places,
            )
        except SQLAlchemyError as exc:
            raise AppError(
                ErrorCode.DB_ERROR,
                "일정을 저장하는 중 오류가 발생했습니다.",
                status_code=500,
            ) from exc
        return _to_response(schedule)

    def update_schedule(
        self,
        current_user: CurrentUser,
        schedule_id: UUID,
        payload: ScheduleUpdateRequest,
    ) -> ScheduleResponse:
        schedule = self.schedules.get_owned(schedule_id, current_user.id)
        if schedule is None:
            raise AppError(
                ErrorCode.SCHEDULE_NOT_FOUND,
                "일정을 찾을 수 없습니다.",
                status_code=404,
            )

        fields = payload.model_dump(exclude_unset=True)
        status = fields.get("status")
        if status is not None:
            fields["status"] = _validate_status(status)

        try:
            kwargs: dict = {}
            if "title" in fields:
                kwargs["title"] = fields["title"]
            if "travel_date" in fields:
                kwargs["travel_date"] = fields["travel_date"]
            if "region_code" in fields:
                kwargs["region_code"] = fields["region_code"]
            if "status" in fields:
                kwargs["status"] = fields["status"]
            if "places" in fields:
                kwargs["places"] = payload.places
            schedule = self.schedules.update(schedule, **kwargs)
        except SQLAlchemyError as exc:
            raise AppError(
                ErrorCode.DB_ERROR,
                "일정을 수정하는 중 오류가 발생했습니다.",
                status_code=500,
            ) from exc
        return _to_response(schedule)

    def delete_schedule(self, current_user: CurrentUser, schedule_id: UUID) -> None:
        schedule = self.schedules.get_owned(schedule_id, current_user.id)
        if schedule is None:
            raise AppError(
                ErrorCode.SCHEDULE_NOT_FOUND,
                "일정을 찾을 수 없습니다.",
                status_code=404,
            )
        try:
            self.schedules.delete(schedule)
        except SQLAlchemyError as exc:
            raise AppError(
                ErrorCode.DB_ERROR,
                "일정을 삭제하는 중 오류가 발생했습니다.",
                status_code=500,
            ) from exc
