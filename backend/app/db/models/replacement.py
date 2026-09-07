"""장소 교체 이력(replacement) ORM."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Replacement(Base):
    __tablename__ = "replacement"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trip_place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_place.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_place_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    to_place_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    ranking_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recommendation_ranking.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    before_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    after_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
