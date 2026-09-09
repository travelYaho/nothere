"""홈 화면용 요약 데이터를 조립하는 서비스이다."""
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.db.models.trip import Trip
from app.repositories.trip_repository import TripRepository
from app.schemas.home import HomeResponse, HomeUserResponse, ScheduleSummary
from app.schemas.user import CurrentUser


# HomeResponse 필드명(schedule_id/draft_schedule/recent_schedules)은 이미 프론트에
# 배포된 홈 화면 계약이라 도메인이 Trip으로 바뀌어도 의도적으로 그대로 유지한다.
def _to_summary(trip: Trip) -> ScheduleSummary:
    """Trip ORM 객체를 홈 응답용 요약 스키마로 변환한다."""
    return ScheduleSummary(
        schedule_id=trip.id,
        title=trip.title,
        travel_date=trip.travel_date,
        status=trip.status,
    )


class HomeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripRepository(db)

    def get_home(self, current_user: CurrentUser) -> HomeResponse:
        try:
            draft = self.trips.get_in_progress(current_user.id)
            recent = self.trips.get_recent(
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
            user=HomeUserResponse(
                id=current_user.id,
                nickname=current_user.nickname,
                profile_image_url=current_user.profile_image_url,
            ),
            draft_schedule=_to_summary(draft) if draft else None,
            recent_schedules=[_to_summary(trip) for trip in recent],
        )
