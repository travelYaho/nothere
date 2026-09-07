"""TourAPI 기준 장소(place) ORM. location 은 PostGIS GEOGRAPHY."""
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.db.base import Base


class Geography(UserDefinedType):
    """PostGIS GEOGRAPHY 컬럼용 최소 타입 (좌표는 리포지토리에서 ST_X/ST_Y 로 읽음)."""

    cache_ok = True

    def get_col_spec(self, **_kwargs: Any) -> str:
        return "GEOGRAPHY(POINT,4326)"


class Place(Base):
    __tablename__ = "place"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tour_content_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    region_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[Any | None] = mapped_column(Geography, nullable=True)
    is_recommendable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
