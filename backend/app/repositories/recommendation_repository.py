"""추천·교체·일정 관련 repository."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.db.models.guide_entry import GuideEntry
from app.db.models.place import Place
from app.db.models.recommendation import (
    RecommendationCandidate,
    RecommendationInteraction,
    RecommendationRanking,
    RecommendationReason,
    RecommendationRequest,
    RecommendationRoute,
    TripPlaceAnalysis,
)
from app.db.models.replacement import Replacement
from app.db.models.share_link import ShareLink
from app.db.models.trip import Trip
from app.db.models.trip_place import TripPlace


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # —— trip / trip_place ——
    def get_trip_owned(self, trip_id: UUID, user_id: UUID) -> Trip | None:
        return (
            self.db.query(Trip)
            .options(joinedload(Trip.places))
            .filter(Trip.id == trip_id, Trip.user_id == user_id)
            .first()
        )

    def get_trip(self, trip_id: UUID) -> Trip | None:
        return (
            self.db.query(Trip)
            .options(joinedload(Trip.places))
            .filter(Trip.id == trip_id)
            .first()
        )

    def get_trip_place(self, trip_place_id: UUID) -> TripPlace | None:
        return self.db.query(TripPlace).filter(TripPlace.id == trip_place_id).first()

    def get_place(self, place_id: UUID) -> Place | None:
        return self.db.query(Place).filter(Place.id == place_id).first()

    def neighbors(
        self, trip_id: UUID, position: int
    ) -> tuple[TripPlace | None, TripPlace | None]:
        places = (
            self.db.query(TripPlace)
            .filter(TripPlace.trip_id == trip_id)
            .order_by(TripPlace.position.asc())
            .all()
        )
        prev_p = next_p = None
        for p in places:
            if p.position < position:
                prev_p = p
            elif p.position > position and next_p is None:
                next_p = p
        return prev_p, next_p

    def latest_analysis(self, trip_place_id: UUID) -> TripPlaceAnalysis | None:
        return (
            self.db.query(TripPlaceAnalysis)
            .filter(TripPlaceAnalysis.trip_place_id == trip_place_id)
            .order_by(desc(TripPlaceAnalysis.analyzed_at))
            .first()
        )

    def remaining_congested(self, trip_id: UUID) -> list[tuple[TripPlace, TripPlaceAnalysis | None]]:
        places = (
            self.db.query(TripPlace)
            .filter(
                TripPlace.trip_id == trip_id,
                TripPlace.resolution_status == "pending",
                TripPlace.is_fixed.is_(False),
            )
            .order_by(TripPlace.position.asc())
            .all()
        )
        items: list[tuple[TripPlace, TripPlaceAnalysis | None]] = []
        for tp in places:
            analysis = self.latest_analysis(tp.id)
            if analysis and analysis.analysis_status == "success" and analysis.level == "high":
                items.append((tp, analysis))
        return items

    # —— recommendation ——
    def get_request(self, request_id: UUID) -> RecommendationRequest | None:
        return (
            self.db.query(RecommendationRequest)
            .filter(RecommendationRequest.id == request_id)
            .first()
        )

    def list_candidates(self, request_id: UUID) -> list[RecommendationCandidate]:
        return (
            self.db.query(RecommendationCandidate)
            .filter(RecommendationCandidate.request_id == request_id)
            .order_by(desc(RecommendationCandidate.experience_score))
            .all()
        )

    def get_candidate(self, candidate_id: UUID) -> RecommendationCandidate | None:
        return (
            self.db.query(RecommendationCandidate)
            .filter(RecommendationCandidate.id == candidate_id)
            .first()
        )

    def get_ranking_by_candidate(self, candidate_id: UUID) -> RecommendationRanking | None:
        return (
            self.db.query(RecommendationRanking)
            .filter(RecommendationRanking.candidate_id == candidate_id)
            .first()
        )

    def get_route_by_candidate(self, candidate_id: UUID) -> RecommendationRoute | None:
        return (
            self.db.query(RecommendationRoute)
            .filter(RecommendationRoute.candidate_id == candidate_id)
            .first()
        )

    def get_reason_by_candidate(self, candidate_id: UUID) -> RecommendationReason | None:
        return (
            self.db.query(RecommendationReason)
            .filter(RecommendationReason.candidate_id == candidate_id)
            .first()
        )

    def upsert_ranking(self, ranking: RecommendationRanking) -> RecommendationRanking:
        existing = self.get_ranking_by_candidate(ranking.candidate_id)
        if existing is None:
            self.db.add(ranking)
            self.db.flush()
            return ranking
        for field in (
            "route_score",
            "congestion_score",
            "operation_score",
            "total_score",
            "rank",
            "scored_at",
        ):
            setattr(existing, field, getattr(ranking, field))
        self.db.flush()
        return existing

    def upsert_route(self, route: RecommendationRoute) -> RecommendationRoute:
        existing = self.get_route_by_candidate(route.candidate_id)
        if existing is None:
            self.db.add(route)
            self.db.flush()
            return route
        for field in (
            "distance_prev_m",
            "distance_next_m",
            "extra_minutes",
            "route_source",
            "is_route_estimated",
            "calculated_at",
        ):
            setattr(existing, field, getattr(route, field))
        self.db.flush()
        return existing

    def upsert_reason(self, reason: RecommendationReason) -> RecommendationReason:
        existing = self.get_reason_by_candidate(reason.candidate_id)
        if existing is None:
            self.db.add(reason)
            self.db.flush()
            return reason
        for field in (
            "recommend_reason",
            "not_recommend_reason",
            "reason_source_snapshot",
            "is_eligible",
            "exclusion_reason",
        ):
            setattr(existing, field, getattr(reason, field))
        self.db.flush()
        return existing

    def list_scored_for_request(
        self, request_id: UUID, *, eligible_only: bool = False
    ) -> list[
        tuple[
            RecommendationCandidate,
            RecommendationRanking,
            RecommendationRoute | None,
            RecommendationReason | None,
        ]
    ]:
        query = (
            self.db.query(
                RecommendationCandidate,
                RecommendationRanking,
                RecommendationRoute,
                RecommendationReason,
            )
            .join(
                RecommendationRanking,
                RecommendationRanking.candidate_id == RecommendationCandidate.id,
            )
            .outerjoin(
                RecommendationRoute,
                RecommendationRoute.candidate_id == RecommendationCandidate.id,
            )
            .outerjoin(
                RecommendationReason,
                RecommendationReason.candidate_id == RecommendationCandidate.id,
            )
            .filter(RecommendationCandidate.request_id == request_id)
        )
        if eligible_only:
            query = query.filter(RecommendationReason.is_eligible.is_(True))
        return list(query.order_by(RecommendationRanking.route_score.desc().nullslast()).all())

    # —— replacement ——
    def create_replacement(self, replacement: Replacement) -> Replacement:
        self.db.add(replacement)
        self.db.flush()
        return replacement

    def get_replacement(self, replacement_id: UUID) -> Replacement | None:
        return self.db.query(Replacement).filter(Replacement.id == replacement_id).first()

    def active_replacement(self, trip_place_id: UUID) -> Replacement | None:
        return (
            self.db.query(Replacement)
            .filter(
                Replacement.trip_place_id == trip_place_id,
                Replacement.reverted_at.is_(None),
            )
            .order_by(desc(Replacement.applied_at))
            .first()
        )

    # —— share / guide ——
    def create_share_link(self, link: ShareLink) -> ShareLink:
        self.db.add(link)
        self.db.flush()
        return link

    def get_share_by_token(self, token: str) -> ShareLink | None:
        return self.db.query(ShareLink).filter(ShareLink.token == token).first()

    def guide_entries(self, trip_id: UUID) -> list[GuideEntry]:
        return (
            self.db.query(GuideEntry)
            .filter(GuideEntry.trip_id == trip_id)
            .order_by(GuideEntry.display_order.asc().nullslast())
            .all()
        )

    def log_interaction(
        self,
        *,
        user_id: UUID,
        trip_id: UUID,
        trip_place_id: UUID,
        event_type: str,
        ranking_id: UUID | None = None,
        position: int | None = None,
    ) -> None:
        self.db.add(
            RecommendationInteraction(
                user_id=user_id,
                trip_id=trip_id,
                trip_place_id=trip_place_id,
                ranking_id=ranking_id,
                event_type=event_type,
                position=position,
                created_at=datetime.now(timezone.utc),
            )
        )
