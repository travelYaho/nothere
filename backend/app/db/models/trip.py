"""여행 일정(trip) ORM — Part1."""
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.trip_place import TripPlace


class Trip(Base):
    __tablename__ = "trip"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profile.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    region_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("region.id"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    travel_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    companion_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transport_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extra_time_limit_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    current_step: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    needs_reanalysis: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    places: Mapped[list["TripPlace"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripPlace.position",
    )
