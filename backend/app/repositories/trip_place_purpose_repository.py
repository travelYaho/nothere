"""trip_place_purposes 테이블에 대한 SQLAlchemy 접근을 모아 둔 repository 이다."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.trip import TripPlacePurpose


class TripPlacePurposeRepository:
    """방문 목적 태그(다중선택, 0개 이상, 전체 교체) 조회/저장을 담당한다."""
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_trip_place(self, trip_place_id: UUID) -> list[TripPlacePurpose]:
        return (
            self.db.query(TripPlacePurpose)
            .filter(TripPlacePurpose.trip_place_id == trip_place_id)
            .all()
        )

    def replace_all(self, trip_place_id: UUID, purpose_tag_ids: list[int]) -> None:
        """기존 선택을 전부 지우고 새로 저장한다(PUT = 전체 교체)."""
        self.db.query(TripPlacePurpose).filter(
            TripPlacePurpose.trip_place_id == trip_place_id
        ).delete()
        self.db.add_all(
            [
                TripPlacePurpose(trip_place_id=trip_place_id, purpose_tag_id=tag_id)
                for tag_id in purpose_tag_ids
            ]
        )
        self.db.commit()
