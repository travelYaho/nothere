"""places 테이블에 대한 SQLAlchemy 접근을 모아 둔 repository 이다."""
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from app.db.models.place import Place, PlaceExperienceTag


class PlaceRepository:
    """TourAPI 검색 결과를 내부 Place 로 get-or-create 하는 역할을 담당한다."""
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, place_id: UUID) -> Place | None:
        return self.db.get(Place, place_id)

    def get_by_source(self, source_type: str, tour_content_id: str) -> Place | None:
        """같은 TourAPI 컨텐츠가 이미 저장돼 있으면 재사용하기 위한 조회."""
        if not tour_content_id:
            return None
        return (
            self.db.query(Place)
            .filter(Place.source_type == source_type, Place.tour_content_id == tour_content_id)
            .first()
        )

    def create(
        self,
        *,
        source_type: str,
        tour_content_id: str | None,
        region_id: int | None,
        name: str,
        longitude: float | None,
        latitude: float | None,
        is_recommendable: bool = True,
        expected_wait_minutes: int | None = None,
        address: str | None = None,
    ) -> Place:
        location = None
        if longitude is not None and latitude is not None:
            location = WKTElement(f"POINT({longitude} {latitude})", srid=4326)

        place = Place(
            source_type=source_type,
            tour_content_id=tour_content_id,
            region_id=region_id,
            name=name,
            location=location,
            is_recommendable=is_recommendable,
            expected_wait_minutes=expected_wait_minutes,
            address=address,
        )
        self.db.add(place)
        self.db.commit()
        self.db.refresh(place)
        return place

    def add_experience_tag(
        self,
        place_id: UUID,
        experience_tag_id: int,
        *,
        weight: float = 1.0,
        source: str = "user_manual",
    ) -> None:
        """장소 직접 추가 시 선택한 '분류'를 place_experience_tags 에 연결한다."""
        self.db.add(
            PlaceExperienceTag(
                place_id=place_id,
                experience_tag_id=experience_tag_id,
                weight=weight,
                source=source,
            )
        )
        self.db.commit()
