"""집중도 분석·추천 요청/후보·랭킹·인터랙션 ORM."""
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TripPlaceAnalysis(Base):
    __tablename__ = "trip_place_analysis"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trip_place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_place.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_status: Mapped[str] = mapped_column(String(20), nullable=False)
    level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    unknown_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class RecommendationRequest(Base):
    __tablename__ = "recommendation_request"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trip_place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_place.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    search_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="default")
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecommendationCandidate(Base):
    __tablename__ = "recommendation_candidate"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recommendation_request.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_place_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    experience_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    congestion_level: Mapped[str] = mapped_column(String(20), nullable=False)
    feasibility_status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class RecommendationRanking(Base):
    __tablename__ = "recommendation_ranking"
    __table_args__ = (UniqueConstraint("candidate_id", name="uq_recommendation_ranking_candidate"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recommendation_candidate.id", ondelete="CASCADE"),
        nullable=False,
    )
    route_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    distance_prev_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_next_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    route_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_route_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    congestion_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    congestion_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    operation_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    rank: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_source_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class RecommendationInteraction(Base):
    __tablename__ = "recommendation_interaction"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    trip_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    trip_place_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    ranking_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    position: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
