"""일정·장소 CRUD. 모든 조회/변경은 user_id(소유자)로 한정한다."""
from uuid import UUID

from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import Session, joinedload

from app.db.models.schedule import IN_PROGRESS_STATUSES, Schedule
from app.db.models.schedule_place import SchedulePlace
from app.schemas.schedule import PlaceCreate


class ScheduleRepository:
    """로그인 사용자 소유의 일정만 다루며, 홈 요약·CRUD에 공용으로 쓴다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_in_progress(self, user_id: UUID) -> Schedule | None:
        return (
            self.db.query(Schedule)
            .filter(Schedule.user_id == user_id, Schedule.status.in_(IN_PROGRESS_STATUSES))
            .order_by(desc(Schedule.updated_at))
            .first()
        )

    def get_recent(
        self,
        user_id: UUID,
        exclude_id: UUID | None = None,
        limit: int = 5,
    ) -> list[Schedule]:
        query = self.db.query(Schedule).filter(
            Schedule.user_id == user_id,
            ~Schedule.status.in_(IN_PROGRESS_STATUSES),
        )
        if exclude_id is not None:
            query = query.filter(Schedule.id != exclude_id)
        return (
            query.order_by(nulls_last(desc(Schedule.travel_date)), desc(Schedule.updated_at))
            .limit(limit)
            .all()
        )

    def list_by_user(self, user_id: UUID) -> list[Schedule]:
        return (
            self.db.query(Schedule)
            .options(joinedload(Schedule.places))
            .filter(Schedule.user_id == user_id)
            .order_by(desc(Schedule.updated_at))
            .all()
        )

    def get_owned(self, schedule_id: UUID, user_id: UUID) -> Schedule | None:
        return (
            self.db.query(Schedule)
            .options(joinedload(Schedule.places))
            .filter(Schedule.id == schedule_id, Schedule.user_id == user_id)
            .first()
        )

    def create(
        self,
        user_id: UUID,
        title: str,
        travel_date,
        region_code: str | None,
        status: str,
        places: list[PlaceCreate],
    ) -> Schedule:
        schedule = Schedule(
            user_id=user_id,
            title=title,
            travel_date=travel_date,
            region_code=region_code,
            status=status,
            places=[
                SchedulePlace(
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
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return self.get_owned(schedule.id, user_id) or schedule

    def update(
        self,
        schedule: Schedule,
        *,
        title: str | None = None,
        travel_date=...,
        region_code=...,
        status: str | None = None,
        places: list[PlaceCreate] | None = None,
    ) -> Schedule:
        if title is not None:
            schedule.title = title
        if travel_date is not ...:
            schedule.travel_date = travel_date
        if region_code is not ...:
            schedule.region_code = region_code
        if status is not None:
            schedule.status = status
        if places is not None:
            schedule.places.clear()
            for p in places:
                schedule.places.append(
                    SchedulePlace(
                        name=p.name,
                        latitude=p.latitude,
                        longitude=p.longitude,
                        address=p.address,
                        order_index=p.order_index,
                        stay_minutes=p.stay_minutes,
                        external_id=p.external_id,
                    )
                )
        self.db.commit()
        return self.get_owned(schedule.id, schedule.user_id) or schedule

    def delete(self, schedule: Schedule) -> None:
        self.db.delete(schedule)
        self.db.commit()
