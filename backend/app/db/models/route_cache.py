"""경로 캐시(route_cache) ORM."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RouteCache(Base):
    __tablename__ = "route_cache"
    __table_args__ = (
        UniqueConstraint(
            "origin_place_id",
            "destination_place_id",
            "transport_mode",
            "provider",
            name="uq_route_cache_od_mode_provider",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    origin_place_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    destination_place_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    transport_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
