"""일정 내 장소(trip_place) ORM — Part1 ERD."""
from datetime import time
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, SmallInteger, String, Time
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.trip import Trip


class TripPlace(Base):
    __tablename__ = "trip_place"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    place_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    initial_place_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    visit_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    stay_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_fixed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    trip: Mapped["Trip"] = relationship(back_populates="places")
