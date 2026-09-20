"""trip_places 테이블에 대한 SQLAlchemy 접근을 모아 둔 repository 이다."""
from datetime import time
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.place import Place
from app.db.models.trip import Trip
from app.db.models.trip_place import TripPlace


class TripPlaceRepository:
    """Trip 에 등록된 장소 추가/중복확인/순서계산을 담당한다."""
    def __init__(self, db: Session) -> None:
        self.db = db

    def exists(self, trip_id: UUID, place_id: UUID) -> bool:
        """같은 장소를 같은 Trip 에 중복 등록하려는지 확인한다(409 duplicate_place_id)."""
        return (
            self.db.query(TripPlace)
            .filter(TripPlace.trip_id == trip_id, TripPlace.place_id == place_id)
            .first()
            is not None
        )

    def next_position(self, trip_id: UUID) -> int:
        """새 장소를 맨 뒤(position+1)에 추가하기 위한 다음 순번을 계산한다."""
        max_position = (
            self.db.query(func.max(TripPlace.position))
            .filter(TripPlace.trip_id == trip_id)
            .scalar()
        )
        return (max_position or 0) + 1

    def add(
        self,
        *,
        trip_id: UUID,
        place_id: UUID,
        position: int,
        visit_time: time | None = None,
    ) -> TripPlace:
        """장소를 추가한다. initial_place_id 는 이후 교체 로직(파트3)이 원래
        장소와 비교할 수 있도록 최초 등록 시점의 place_id 와 동일하게 둔다.
        """
        trip_place = TripPlace(
            trip_id=trip_id,
            place_id=place_id,
            initial_place_id=place_id,
            position=position,
            visit_time=visit_time,
        )
        self.db.add(trip_place)
        self.db.commit()
        self.db.refresh(trip_place)
        return trip_place

    def get_owned_by_id(self, trip_place_id: UUID, user_id: UUID) -> TripPlace | None:
        """URL 에 tripId 가 없는 엔드포인트(PATCH/DELETE trip-places/{id})용으로
        Trip 을 조인해 현재 사용자 소유인지까지 함께 확인한다.
        """
        return (
            self.db.query(TripPlace)
            .join(Trip, Trip.id == TripPlace.trip_id)
            .filter(TripPlace.id == trip_place_id, Trip.user_id == user_id)
            .first()
        )

    def get_owned_by_ids(self, trip_id: UUID, trip_place_ids: list[UUID], user_id: UUID) -> list[TripPlace]:
        """순서변경 요청에 포함된 tripPlaceId 들이 전부 이 Trip 소유인지 확인할 때 쓴다."""
        return (
            self.db.query(TripPlace)
            .join(Trip, Trip.id == TripPlace.trip_id)
            .filter(
                TripPlace.id.in_(trip_place_ids),
                TripPlace.trip_id == trip_id,
                Trip.user_id == user_id,
            )
            .all()
        )

    def first_place(self, trip_id: UUID) -> Place | None:
        """일정 첫 장소. 홈 추천 배너가 캐시된 표지가 없을 때 폴백 이미지를 고르는 데 쓴다."""
        return (
            self.db.query(Place)
            .join(TripPlace, TripPlace.place_id == Place.id)
            .filter(TripPlace.trip_id == trip_id)
            .order_by(TripPlace.position.asc())
            .first()
        )

    def count_by_trip(self, trip_id: UUID) -> int:
        """최소 장소 수(minimum_places_required) 검증에 쓰는 현재 등록 수."""
        return self.db.query(TripPlace).filter(TripPlace.trip_id == trip_id).count()

    def count_by_trips(self, trip_ids: list[UUID]) -> dict[UUID, int]:
        """여러 Trip의 장소 수를 한 번에 센다(홈/보관함 목록용).

        count_by_trip()을 목록 건수만큼 반복 호출하면(홈 최대 6건, 보관함 페이지당
        최대 10건) 그만큼 COUNT 쿼리가 반복된다 — trip_summary.build_*_summary()가
        건마다 부르던 걸 여기서 GROUP BY 한 번으로 대체한다. 결과에 없는 trip_id는
        장소가 0개라는 뜻이므로 호출부가 `.get(trip_id, 0)`으로 처리한다.
        """
        if not trip_ids:
            return {}
        rows = (
            self.db.query(TripPlace.trip_id, func.count(TripPlace.id))
            .filter(TripPlace.trip_id.in_(trip_ids))
            .group_by(TripPlace.trip_id)
            .all()
        )
        return dict(rows)

    def delete(self, trip_place: TripPlace) -> None:
        self.db.delete(trip_place)
        self.db.commit()

    def reorder(self, positions: dict[UUID, int]) -> None:
        """{tripPlaceId: 새 position} 매핑을 한 번에 반영한다."""
        for trip_place_id, position in positions.items():
            self.db.query(TripPlace).filter(TripPlace.id == trip_place_id).update({"position": position})
        self.db.commit()

    def update_visit(
        self,
        trip_place: TripPlace,
        *,
        visit_time: time | None,
        duration_minutes: int | None,
        is_fixed: bool | None,
        fields: dict,
    ) -> TripPlace:
        """제공된 필드만 갱신한다(exclude_unset 기준)."""
        if "visit_time" in fields:
            trip_place.visit_time = visit_time
        if "duration_minutes" in fields:
            trip_place.stay_minutes = duration_minutes
        if "is_fixed" in fields:
            trip_place.is_fixed = is_fixed
        self.db.commit()
        self.db.refresh(trip_place)
        return trip_place
