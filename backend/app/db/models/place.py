"""장소(관광지) 및 장소-경험태그 매핑을 저장하는 모델이다.

`location` 은 스키마 문서 원본대로 PostGIS GEOGRAPHY(POINT) 로 저장한다.
Part3(홍수민) 의 경로/거리 계산이 이 컬럼을 직접 쓸 수 있어야 하므로
latitude/longitude 컬럼으로 바꾸지 않는다. 검색 결과 표시용 address/category
같은 부가 정보는 이 공유 테이블에 넣지 않고, 필요하면 /places/search 를
구현하는 쪽에서 TourAPI 응답을 그대로 내려주거나 별도 캐시 테이블을 둔다.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experience_tag import ExperienceTag
    from app.db.models.region import Region
    from app.db.models.trip import TripPlace


class Place(Base):
    """TourAPI 등에서 수집한 장소 기준 정보를 저장하는 places 모델."""
    __tablename__ = "places"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="tour_api")
    tour_content_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    region_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    is_recommendable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    region: Mapped["Region | None"] = relationship(back_populates="places")
    experience_tags: Mapped[list["PlaceExperienceTag"]] = relationship(back_populates="place")
    trip_places: Mapped[list["TripPlace"]] = relationship(
        back_populates="place",
        foreign_keys="TripPlace.place_id",
    )


class PlaceExperienceTag(Base):
    """장소가 어떤 경험 태그와 얼마나 관련 있는지 저장하는 복합키 매핑 모델."""
    __tablename__ = "place_experience_tags"

    place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        primary_key=True,
    )
    experience_tag_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("experience_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weight: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=1.0)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="tour_category")

    place: Mapped["Place"] = relationship(back_populates="experience_tags")
    experience_tag: Mapped["ExperienceTag"] = relationship(back_populates="place_tags")
