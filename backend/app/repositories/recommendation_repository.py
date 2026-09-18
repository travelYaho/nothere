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
            .options(joinedload(Trip.trip_places), joinedload(Trip.region))
            .filter(Trip.id == trip_id, Trip.user_id == user_id)
            .first()
        )

    def get_trip(self, trip_id: UUID) -> Trip | None:
        return (
            self.db.query(Trip)
            .options(joinedload(Trip.trip_places), joinedload(Trip.region))
            .filter(Trip.id == trip_id)
            .first()
        )

    def get_trip_place(self, trip_place_id: UUID) -> TripPlace | None:
        return self.db.query(TripPlace).filter(TripPlace.id == trip_place_id).first()

    def get_trip_place_for_update(self, trip_place_id: UUID) -> TripPlace | None:
        """교체 적용/취소 전 행을 잠그고, 잠금 시점의 값을 읽는다.

        같은 trip_place가 이미 이 세션의 identity map에 로드돼 있으면(예: 호출부가 이
        메서드보다 먼저 get_trip_place()를 불렀으면) populate_existing() 없이는
        SELECT ... FOR UPDATE로 잠가도 캐시된 옛 속성값을 그대로 돌려준다 — 잠금 자체는
        DB 레벨에서 걸리지만 Python 쪽 객체가 안 갱신된다. apply_replacement()/
        revert_replacement()는 이 메서드를 그 trip_place에 대한 첫(유일한) 조회로 써서
        이 함정을 피한다.
        """
        return (
            self.db.query(TripPlace)
            .filter(TripPlace.id == trip_place_id)
            .populate_existing()
            .with_for_update()
            .first()
        )

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

    def get_candidate_for_trip_place(
        self, candidate_id: UUID, trip_place_id: UUID
    ) -> RecommendationCandidate | None:
        """candidate가 실제로 이 trip_place의 추천 요청에서 나온 것인지까지 확인해서 조회한다.

        id만으로 조회하면(get_candidate()) 다른 trip_place는 물론 다른 사용자의
        candidate_id를 넘겨도 그대로 통과한다 — candidate.request_id ->
        recommendation_request.trip_place_id 체인까지 같이 검증한다. 교체 적용
        (apply_replacement)은 이 메서드로만 candidate를 조회해야 한다.
        """
        return (
            self.db.query(RecommendationCandidate)
            .join(
                RecommendationRequest,
                RecommendationCandidate.request_id == RecommendationRequest.id,
            )
            .filter(
                RecommendationCandidate.id == candidate_id,
                RecommendationRequest.trip_place_id == trip_place_id,
            )
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
                SELECT id, name, tour_content_id, area_cd, signgu_cd,
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

        이미 그 (place, tag) 조합에 값이 있으면(source가 무엇이든) 절대 덮어쓰지 않고,
        없는 조합만 새로 채운다.

        예전엔 `source IS DISTINCT FROM 'manual'`일 때만 덮어써서 "manual"이 아닌 기존
        값은 매번 새로 추정한 값으로 갈아치웠다 — 그런데 STEP6 점수 계산
        (resolve_experience_score)은 "저장값이 있으면 그 값을 그대로 믿는다"는 정책이라,
        이 둘이 서로 달라서 "이번 점수는 저장된 낮은 값으로 계산했는데, 후보 선택과
        동시에 그 값이 훨씬 높은 새 추정치로 조용히 바뀌는" 불일치가 있었다(코드 리뷰로
        발견, 2026-09-16). 게다가 실제 공유 DB를 조회해보니 `source='user_manual'`인
        진짜 수동 태그가 11건 있었는데, 이건 "manual"과 다른 문자열이라 저 가드로는 전혀
        보호되지 않고 있었다 — 이번 방식(있으면 절대 안 건드림)으로 바꾸면 그 문자열이
        뭐든 상관없이 안전하게 보호된다.
        """
        for tag_id, weight in weights.items():
            insert_stmt = pg_insert(PlaceExperienceTag).values(
                place_id=place_id,
                experience_tag_id=tag_id,
                weight=Decimal(str(round(weight, 4))),
                source=source,
            )
            stmt = insert_stmt.on_conflict_do_nothing(
                index_elements=["place_id", "experience_tag_id"]
            )
            self.db.execute(stmt)
        self.db.flush()

    def list_experience_tags_for_places(
        self, place_ids: list[UUID]
    ) -> dict[UUID, list[PlaceExperienceTag]]:
        """여러 place의 place_experience_tag를 한 번에 조회한다(place_id -> 행 목록).

        STEP6(enrich_candidates)이 후보마다 개별 조회하면 후보 수만큼 쿼리가 나가므로
        일괄 조회로 묶는다 — get_by_sources()와 같은 이유.
        """
        if not place_ids:
            return {}
        rows = (
            self.db.query(PlaceExperienceTag)
            .filter(PlaceExperienceTag.place_id.in_(place_ids))
            .all()
        )
        result: dict[UUID, list[PlaceExperienceTag]] = {}
        for row in rows:
            result.setdefault(row.place_id, []).append(row)
        return result

    def list_place_tags_map(self, place_ids: list[UUID]) -> dict[UUID, list[dict]]:
        """place_id → [{id, name}] 경험 태그. 가중치 높은 순."""
        if not place_ids:
            return {}
        rows = (
            self.db.query(PlaceExperienceTag, ExperienceTag)
            .join(ExperienceTag, ExperienceTag.id == PlaceExperienceTag.experience_tag_id)
            .filter(PlaceExperienceTag.place_id.in_(place_ids))
            .order_by(PlaceExperienceTag.weight.desc(), ExperienceTag.display_order.asc())
            .all()
        )
        result: dict[UUID, list[dict]] = {}
        seen: dict[UUID, set[int]] = {}
        for pet, tag in rows:
            already = seen.setdefault(pet.place_id, set())
            if tag.id in already:
                continue
            already.add(tag.id)
            result.setdefault(pet.place_id, []).append({"id": tag.id, "name": tag.name})
        return result

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
        """그 trip_place에서 아직 되돌리지 않은(reverted_at IS NULL) 가장 최근 교체.

        applied_at만으로 정렬하면 동시에 같은 타임스탬프로 기록된 경우(이론상 가능) 결과가
        비결정적일 수 있어, id를 보조 정렬 키로 둬서 항상 같은 행을 돌려주게 한다.
        """
        return (
            self.db.query(Replacement)
            .filter(
                Replacement.trip_place_id == trip_place_id,
                Replacement.reverted_at.is_(None),
            )
            .order_by(desc(Replacement.applied_at), desc(Replacement.id))
            .first()
        )

    # —— share / guide ——
    def create_share_link(self, link: ShareLink) -> ShareLink:
        self.db.add(link)
        self.db.flush()
        return link

    def get_active_share_link(self, trip_id: UUID) -> ShareLink | None:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(ShareLink)
            .filter(ShareLink.trip_id == trip_id)
            .filter(ShareLink.revoked_at.is_(None))
            .filter((ShareLink.expires_at.is_(None)) | (ShareLink.expires_at > now))
            .order_by(ShareLink.created_at.desc(), ShareLink.id.desc())
            .first()
        )

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
