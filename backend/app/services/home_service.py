"""홈 화면용 요약 데이터를 조립하는 서비스이다."""
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.repositories.trip_place_repository import TripPlaceRepository
from app.repositories.trip_repository import TripRepository
from app.schemas.home import HomeResponse, HomeUserResponse
from app.schemas.user import CurrentUser
from app.services.trip_summary import build_schedule_summary


# HomeResponse 필드명(schedule_id/draft_schedule/recent_schedules)은 이미 프론트에
# 배포된 홈 화면 계약이라 도메인이 Trip으로 바뀌어도 의도적으로 그대로 유지한다.
class HomeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripRepository(db)
        self.trip_places = TripPlaceRepository(db)

    def get_home(self, current_user: CurrentUser) -> HomeResponse:
        try:
            draft = self.trips.get_in_progress(current_user.id)
            recent = self.trips.get_recent(
                current_user.id,
                exclude_id=draft.id if draft else None,
            )
            trips = ([draft] if draft else []) + recent
            place_counts = self.trip_places.count_by_trips([trip.id for trip in trips])
            draft_schedule = (
                build_schedule_summary(draft, place_counts.get(draft.id, 0)) if draft else None
            )
            recent_schedules = [
                build_schedule_summary(trip, place_counts.get(trip.id, 0)) for trip in recent
            ]
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
            draft_schedule=draft_schedule,
            recent_schedules=recent_schedules,
        )
