"""홈 화면 응답을 조합하는 서비스 계층이다.

현재 사용자 정보와 일정 요약을 합쳐 GET /api/home 응답 형태로 반환한다.
"""
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.db.models.schedule import Schedule
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.home import HomeResponse, HomeUserResponse, ScheduleSummary
from app.schemas.user import CurrentUser


def _to_summary(schedule: Schedule) -> ScheduleSummary:
    """Schedule ORM 객체를 홈 응답용 요약 스키마로 변환한다."""
    return ScheduleSummary(
        schedule_id=schedule.id,
        title=schedule.title,
        travel_date=schedule.travel_date,
        status=schedule.status,
    )


class HomeService:
    """홈 라우터가 직접 쿼리를 다루지 않도록 조회 조합을 캡슐화한다."""
    def __init__(self, db: Session) -> None:
        self.db = db
        self.schedules = ScheduleRepository(db)

    # 홈은 요약만 반환한다. 일정 CRUD는 ScheduleService(/api/schedules)를 사용한다.
    def get_home(self, current_user: CurrentUser) -> HomeResponse:
        try:
            draft = self.schedules.get_in_progress(current_user.id)
            recent = self.schedules.get_recent(
                current_user.id,
                exclude_id=draft.id if draft else None,
            )
        except SQLAlchemyError as exc:
            raise AppError(
                ErrorCode.DB_ERROR,
                "홈 정보를 조회하는 중 오류가 발생했습니다.",
                status_code=500,
            ) from exc

        return HomeResponse(
            user=HomeUserResponse(id=current_user.id, nickname=current_user.nickname),
            draft_schedule=_to_summary(draft) if draft else None,
            recent_schedules=[_to_summary(item) for item in recent],
        )
