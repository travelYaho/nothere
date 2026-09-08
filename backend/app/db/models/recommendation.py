"""집중도 분석·추천 요청/후보·순위(Part2)·경로/이유(Part3)·인터랙션."""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    pass


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

    candidates: Mapped[list["RecommendationCandidate"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )


class RecommendationCandidate(Base):
    __tablename__ = "recommendation_candidate"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recommendation_request.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("place.id"),
        nullable=False,
    )
    experience_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    congestion_level: Mapped[str] = mapped_column(String(20), nullable=False)
    feasibility_status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    request: Mapped["RecommendationRequest"] = relationship(back_populates="candidates")
    ranking: Mapped["RecommendationRanking | None"] = relationship(
        back_populates="candidate",
        uselist=False,
        cascade="all, delete-orphan",
    )
    route: Mapped["RecommendationRoute | None"] = relationship(
        back_populates="candidate",
        uselist=False,
        cascade="all, delete-orphan",
    )
    reason: Mapped["RecommendationReason | None"] = relationship(
        back_populates="candidate",
        uselist=False,
        cascade="all, delete-orphan",
    )


class RecommendationRanking(Base):
    """Part2: 점수/순위만. 거리→route, 이유→reason."""

    __tablename__ = "recommendation_ranking"
    __table_args__ = (UniqueConstraint("candidate_id", name="uq_recommendation_ranking_candidate"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recommendation_candidate.id", ondelete="CASCADE"),
        nullable=False,
    )
    route_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    congestion_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    operation_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    rank: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate: Mapped["RecommendationCandidate"] = relationship(back_populates="ranking")


class RecommendationRoute(Base):
    """Part3: candidate를 현재 trip 일정 문맥에서 평가한 경로 정보."""

    __tablename__ = "recommendation_route"
    __table_args__ = (UniqueConstraint("candidate_id", name="uq_recommendation_route_candidate"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recommendation_candidate.id", ondelete="CASCADE"),
        nullable=False,
    )
    distance_prev_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_next_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    route_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_route_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate: Mapped["RecommendationCandidate"] = relationship(back_populates="route")


class RecommendationReason(Base):
    """Part3: 추천/비추천 이유. 실제 선택은 replacement 로 판단 (is_selected 없음)."""

    __tablename__ = "recommendation_reason"
    __table_args__ = (UniqueConstraint("candidate_id", name="uq_recommendation_reason_candidate"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recommendation_candidate.id", ondelete="CASCADE"),
        nullable=False,
    )
    recommend_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    not_recommend_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_source_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
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

    candidate: Mapped["RecommendationCandidate"] = relationship(back_populates="reason")


class RecommendationInteraction(Base):
    __tablename__ = "recommendation_interaction"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth.users.id"),
        nullable=False,
    )
    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trip_place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_place.id", ondelete="CASCADE"),
        nullable=False,
    )
    ranking_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("recommendation_ranking.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    position: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
