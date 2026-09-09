"""홈 화면용 요약 데이터를 조립하는 서비스이다.

draft/recent 는 통합 스키마 trip 테이블에서 조회한다.
HomeResponse.schedule_id 는 trip.id 를 그대로 담는다.
"""
from sqlalchemy.orm import Session

from app.db.models.trip import Trip
from app.repositories.trip_repository import TripRepository
from app.schemas.home import HomeResponse, HomeUserResponse, ScheduleSummary
from app.schemas.user import CurrentUser

RECENT_LIMIT = 10


def _to_summary(trip: Trip) -> ScheduleSummary:
    return ScheduleSummary(
        schedule_id=trip.id,
        title=trip.title,
        travel_date=trip.travel_date,
        status=trip.status,
        place_count=len(trip.places or []),
    )


class HomeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripRepository(db)

    def get_home(self, current_user: CurrentUser) -> HomeResponse:
        trips = self.trips.list_by_user(current_user.id)
        drafts = [trip for trip in trips if trip.status == "draft"]
        draft = drafts[0] if drafts else None
        recent = [trip for trip in trips if draft is None or trip.id != draft.id][:RECENT_LIMIT]
        return HomeResponse(
            user=HomeUserResponse(
                id=current_user.id,
                nickname=current_user.nickname,
                profile_image_url=current_user.profile_image_url,
            ),
            draft_schedule=_to_summary(draft) if draft else None,
            recent_schedules=[_to_summary(trip) for trip in recent],
        )
