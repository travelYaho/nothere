"""현재 사용자 소유의 trip 조회/삭제 repository."""
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.db.models.place import Place
from app.db.models.trip import Trip
from app.db.models.trip_place import TripPlace


class TripRepository:
    """홈·일정 목록/상세가 trip ORM 을 직접 다루지 않도록 감싼다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_user(self, user_id: UUID) -> list[Trip]:
        """최신 생성순으로 사용자 일정을 장소와 함께 조회한다."""
        return (
            self.db.query(Trip)
            .options(joinedload(Trip.places))
            .filter(Trip.user_id == user_id)
            .order_by(Trip.created_at.desc())
            .all()
        )

    def get_owned(self, trip_id: UUID, user_id: UUID) -> Trip | None:
        """소유권이 있는 일정 단건을 장소와 함께 조회한다."""
        return (
            self.db.query(Trip)
            .options(joinedload(Trip.places))
            .filter(Trip.id == trip_id, Trip.user_id == user_id)
            .first()
        )

    def place_names(self, place_ids: list[UUID]) -> dict[UUID, str]:
        """place.id → name 맵. 빈 목록이면 쿼리하지 않는다."""
        if not place_ids:
            return {}
        rows = self.db.query(Place).filter(Place.id.in_(place_ids)).all()
        return {row.id: row.name for row in rows}

    def delete(self, trip: Trip) -> None:
        """trip_place 는 FK CASCADE 로 함께 삭제된다."""
        self.db.delete(trip)
        self.db.commit()
