"""일정 내 장소(trip_place) ORM — Part1."""
from datetime import datetime, time
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Time, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.place import Place
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
    place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("place.id"),
        nullable=False,
        index=True,
    )
    initial_place_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("place.id"),
        nullable=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    visit_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    stay_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=60)
    is_fixed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # ERD 원본엔 없는 필드. 생성/수정 시각 추적용으로 실무적으로 추가했다.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    trip: Mapped["Trip"] = relationship(back_populates="trip_places")
    place: Mapped["Place"] = relationship(foreign_keys=[place_id])
