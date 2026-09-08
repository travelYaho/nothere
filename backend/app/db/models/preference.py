"""여행/장소 경험 태그·목적·장기 선호 — Part1."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TripPlacePurpose(Base):
    __tablename__ = "trip_place_purpose"

    trip_place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_place.id", ondelete="CASCADE"),
        primary_key=True,
    )
    purpose_tag_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("experience_tag.id"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TripPreferredExperience(Base):
    __tablename__ = "trip_preferred_experience"

    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip.id", ondelete="CASCADE"),
        primary_key=True,
    )
    experience_tag_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("experience_tag.id"),
        primary_key=True,
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)


class PlaceExperienceTag(Base):
    __tablename__ = "place_experience_tag"

    place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("place.id", ondelete="CASCADE"),
        primary_key=True,
    )
    experience_tag_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("experience_tag.id"),
        primary_key=True,
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)


class UserLongTermPreference(Base):
    __tablename__ = "user_long_term_preference"
    __table_args__ = (
        UniqueConstraint("user_id", "experience_tag_id", name="uq_user_long_term_preference_user_tag"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    experience_tag_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("experience_tag.id"),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    trip_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
