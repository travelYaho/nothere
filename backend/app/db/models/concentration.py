"""집중률 spot / place 매핑 — Part2."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConcentrationSpot(Base):
    __tablename__ = "concentration_spot"
    __table_args__ = (
        UniqueConstraint("area_cd", "signgu_cd", "tourist_name", name="uq_concentration_spot_area_signgu_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    area_cd: Mapped[str] = mapped_column(String(20), nullable=False)
    signgu_cd: Mapped[str] = mapped_column(String(20), nullable=False)
    tourist_name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(200), nullable=False)


class PlaceConcentrationMapping(Base):
    __tablename__ = "place_concentration_mapping"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("place.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concentration_spot_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("concentration_spot.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_method: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
