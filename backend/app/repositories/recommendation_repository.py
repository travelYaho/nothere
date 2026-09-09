"""추천·교체·일정 관련 repository."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import desc, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload

from app.db.models.experience_tag import ExperienceTag
from app.db.models.guide_entry import GuideEntry
from app.db.models.place import Place
from app.db.models.preference import PlaceExperienceTag
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

    def _execute_upsert(self, stmt):
        # identity-map 에 이미 있는 엔터티면 RETURNING 값으로 속성을 갱신한다.
        row = self.db.execute(
            stmt,
            execution_options={"populate_existing": True},
        ).scalars().first()
        self.db.flush()
        return row

    # —— trip / trip_place ——
    def get_trip_owned(self, trip_id: UUID, user_id: UUID) -> Trip | None:
        return (
            self.db.query(Trip)
            .options(joinedload(Trip.trip_places))
            .filter(Trip.id == trip_id, Trip.user_id == user_id)
            .first()
        )

    def get_trip(self, trip_id: UUID) -> Trip | None:
        return (
            self.db.query(Trip)
            .options(joinedload(Trip.trip_places))
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
        insert_stmt = pg_insert(RecommendationRanking).values(
            id=ranking.id or uuid4(),
            candidate_id=ranking.candidate_id,
            route_score=ranking.route_score,
            congestion_score=ranking.congestion_score,
            operation_score=ranking.operation_score,
            total_score=ranking.total_score,
            rank=ranking.rank,
            scored_at=ranking.scored_at,
        )
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["candidate_id"],
            set_={
                "route_score": insert_stmt.excluded.route_score,
                "congestion_score": insert_stmt.excluded.congestion_score,
                "operation_score": insert_stmt.excluded.operation_score,
                "total_score": insert_stmt.excluded.total_score,
                "rank": insert_stmt.excluded.rank,
                "scored_at": insert_stmt.excluded.scored_at,
            },
        ).returning(RecommendationRanking)
        return self._execute_upsert(stmt)

    def upsert_route(self, route: RecommendationRoute) -> RecommendationRoute:
        insert_stmt = pg_insert(RecommendationRoute).values(
            id=route.id or uuid4(),
            candidate_id=route.candidate_id,
            distance_prev_m=route.distance_prev_m,
            distance_next_m=route.distance_next_m,
            extra_minutes=route.extra_minutes,
            route_source=route.route_source,
            is_route_estimated=route.is_route_estimated,
            calculated_at=route.calculated_at,
        )
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["candidate_id"],
            set_={
                "distance_prev_m": insert_stmt.excluded.distance_prev_m,
                "distance_next_m": insert_stmt.excluded.distance_next_m,
                "extra_minutes": insert_stmt.excluded.extra_minutes,
                "route_source": insert_stmt.excluded.route_source,
                "is_route_estimated": insert_stmt.excluded.is_route_estimated,
                "calculated_at": insert_stmt.excluded.calculated_at,
            },
        ).returning(RecommendationRoute)
        return self._execute_upsert(stmt)

    def upsert_reason(self, reason: RecommendationReason) -> RecommendationReason:
        insert_stmt = pg_insert(RecommendationReason).values(
            id=reason.id or uuid4(),
            candidate_id=reason.candidate_id,
            recommend_reason=reason.recommend_reason,
            not_recommend_reason=reason.not_recommend_reason,
            reason_source_snapshot=reason.reason_source_snapshot,
            is_eligible=reason.is_eligible,
            exclusion_reason=reason.exclusion_reason,
        )
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["candidate_id"],
            set_={
                "recommend_reason": insert_stmt.excluded.recommend_reason,
                "not_recommend_reason": insert_stmt.excluded.not_recommend_reason,
                "reason_source_snapshot": insert_stmt.excluded.reason_source_snapshot,
                "is_eligible": insert_stmt.excluded.is_eligible,
                "exclusion_reason": insert_stmt.excluded.exclusion_reason,
                "updated_at": datetime.now(timezone.utc),
            },
        ).returning(RecommendationReason)
        return self._execute_upsert(stmt)

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

    # —— STEP6 대안 후보 생성 ——
    def list_trip_place_ids(self, trip_id: UUID) -> set[UUID]:
        """같은 일정에 이미 포함된 place_id들 — duplicate_place 판정용."""
        rows = self.db.query(TripPlace.place_id).filter(TripPlace.trip_id == trip_id).all()
        return {row[0] for row in rows}

    def get_places_map(self, place_ids) -> dict[UUID, Place]:
        place_ids = list(place_ids)
        if not place_ids:
            return {}
        rows = self.db.query(Place).filter(Place.id.in_(place_ids)).all()
        return {row.id: row for row in rows}

    def get_or_create_place_by_tour_content_id(
        self, tour_content_id: str, name: str, latitude: float, longitude: float
    ) -> Place:
        place = (
            self.db.query(Place).filter(Place.tour_content_id == tour_content_id).first()
        )
        if place is not None:
            return place
        place = Place(
            source_type="tour_api",
            tour_content_id=tour_content_id,
            name=name,
            is_recommendable=True,
        )
        self.db.add(place)
        self.db.flush()
        self.db.execute(
            text(
                "UPDATE place SET location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography "
                "WHERE id = :id"
            ),
            {"lng": longitude, "lat": latitude, "id": str(place.id)},
        )
        self.db.flush()
        self.db.refresh(place)
        return place

    def list_nearby_recommendable_places(
        self,
        latitude: float,
        longitude: float,
        radius_m: float,
        exclude_place_ids: set[UUID],
        limit: int = 20,
    ) -> list[dict]:
        """TourAPI 응답이 비었을 때 쓰는 DB 후보 풀 — 이미 알려진 place 중 반경 내 것만."""
        rows = self.db.execute(
            text(
                """
                SELECT id, name, tour_content_id,
                       ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng
                FROM place
                WHERE is_recommendable = TRUE
                  AND location IS NOT NULL
                  AND ST_DWithin(
                        location,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                        :radius_m
                      )
                ORDER BY location <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                LIMIT :limit
                """
            ),
            {"lng": longitude, "lat": latitude, "radius_m": radius_m, "limit": limit},
        ).mappings().all()
        return [
            dict(row)
            for row in rows
            if UUID(str(row["id"])) not in exclude_place_ids
        ]

    def get_experience_tag_code_map(self) -> dict[str, int]:
        rows = self.db.query(ExperienceTag).filter(ExperienceTag.is_active.is_(True)).all()
        return {row.code: row.id for row in rows}

    def list_experience_tags(self) -> list[ExperienceTag]:
        return (
            self.db.query(ExperienceTag)
            .filter(ExperienceTag.is_active.is_(True))
            .order_by(ExperienceTag.id.asc())
            .all()
        )

    def upsert_place_experience_tags(
        self, place_id: UUID, weights: dict[int, float], source: str
    ) -> None:
        """카테고리 기반으로 추정한 place-경험태그 가중치를 저장한다.

        source="manual"인 기존 행은 덮어쓰지 않는다 — 수동 검수 UI가 아직 없어 지금 당장
        만들어지는 값은 아니지만, 나중에 사람이 직접 확정한 태그가 다음 추천 요청 때 카테고리
        규칙으로 조용히 되돌려지는 것을 미리 막아둔다(place_concentration_mapping의
        _HUMAN_REVIEWED_STATUSES 보존 규칙과 같은 목적).
        """
        for tag_id, weight in weights.items():
            insert_stmt = pg_insert(PlaceExperienceTag).values(
                place_id=place_id,
                experience_tag_id=tag_id,
                weight=Decimal(str(round(weight, 4))),
                source=source,
            )
            stmt = insert_stmt.on_conflict_do_update(
                index_elements=["place_id", "experience_tag_id"],
                set_={
                    "weight": insert_stmt.excluded.weight,
                    "source": insert_stmt.excluded.source,
                },
                where=PlaceExperienceTag.source.is_distinct_from("manual"),
            )
            self.db.execute(stmt)
        self.db.flush()

    def create_request_with_candidates(
        self,
        trip_place_id: UUID,
        search_mode: str,
        status: str,
        candidates: list[dict],
    ) -> RecommendationRequest:
        """요청 행과 후보 행들을 한 트랜잭션으로 커밋한다.

        요청을 status=success로 먼저 커밋하고 후보 저장을 별도 커밋으로 나누면, 후보 저장이
        실패했을 때 "성공했지만 후보가 없는 요청"이 남을 수 있어 하나의 트랜잭션으로 묶는다.
        """
        request = RecommendationRequest(
            trip_place_id=trip_place_id,
            search_mode=search_mode,
            status=status,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(request)
        self.db.flush()  # candidates가 참조할 request.id 확보
        for candidate in candidates:
            self.db.add(RecommendationCandidate(request_id=request.id, **candidate))
        self.db.commit()
        self.db.refresh(request)
        return request

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
