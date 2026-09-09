"""일정 목록·상세·삭제 비즈니스 로직."""
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.db.models.trip import Trip
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import (
    TripDetailResponse,
    TripListItem,
    TripListResponse,
    TripPlaceItem,
)
from app.schemas.user import CurrentUser


def _place_count(trip: Trip) -> int:
    return len(trip.places or [])


class TripService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripRepository(db)

    def list_trips(self, current_user: CurrentUser) -> TripListResponse:
        items = [
            TripListItem(
                id=trip.id,
                title=trip.title,
                travel_date=trip.travel_date,
                status=trip.status,
                current_step=trip.current_step,
                place_count=_place_count(trip),
                created_at=trip.created_at,
            )
            for trip in self.trips.list_by_user(current_user.id)
        ]
        return TripListResponse(items=items)

    def get_trip(self, trip_id: UUID, current_user: CurrentUser) -> TripDetailResponse:
        trip = self.trips.get_owned(trip_id, current_user.id)
        if trip is None:
            raise AppError(
                ErrorCode.SCHEDULE_NOT_FOUND,
                "일정을 찾을 수 없습니다.",
                status_code=404,
            )
        names = self.trips.place_names([place.place_id for place in trip.places])
        places = [
            TripPlaceItem(
                id=place.id,
                place_id=place.place_id,
                name=names.get(place.place_id, ""),
                position=place.position,
                visit_time=place.visit_time,
                stay_minutes=place.stay_minutes,
                resolution_status=place.resolution_status,
            )
            for place in trip.places
        ]
        return TripDetailResponse(
            id=trip.id,
            title=trip.title,
            travel_date=trip.travel_date,
            status=trip.status,
            current_step=trip.current_step,
            region_id=trip.region_id,
            companion_type=trip.companion_type,
            transport_mode=trip.transport_mode,
            extra_time_limit_minutes=trip.extra_time_limit_minutes,
            places=places,
            created_at=trip.created_at,
            confirmed_at=trip.confirmed_at,
        )

    def delete_trip(self, trip_id: UUID, current_user: CurrentUser) -> None:
        trip = self.trips.get_owned(trip_id, current_user.id)
        if trip is None:
            raise AppError(
                ErrorCode.SCHEDULE_NOT_FOUND,
                "일정을 찾을 수 없습니다.",
                status_code=404,
            )
        try:
            self.trips.delete(trip)
        except SQLAlchemyError as exc:
            raise AppError(
                ErrorCode.DB_ERROR,
                "일정을 삭제하는 중 오류가 발생했습니다.",
                status_code=500,
            ) from exc
