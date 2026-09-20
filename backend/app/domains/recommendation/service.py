"""추천 경로 점수·교체·확정·가이드 서비스."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.clients import photo_gallery, tour_api
from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.db.models.recommendation import (
    RecommendationRanking,
    RecommendationReason,
    RecommendationRoute,
)
from app.db.models.replacement import Replacement
from app.db.models.share_link import ShareLink, ShareLinkVisibility
from app.db.models.trip import Trip
from app.domains.analysis.service import AnalysisStatus, ConcentrationLevel, RULE_VERSION
from app.domains.recommendation import candidates as candidate_pipeline
from app.domains.recommendation.route import RouteService
from app.domains.recommendation.scoring import (
    build_reason_text,
    compute_route_score,
    to_decimal,
)
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.place_repository import PlaceRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.user import CurrentUser
from app.utils.geo import get_place_coords
from app.utils.region_display import district_from_text, majority_district, short_city_name


class RecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RecommendationRepository(db)
        self.analysis_repo = AnalysisRepository(db)
        self.places = PlaceRepository(db)
        self.routes = RouteService(db)

    def create_request(
        self,
        trip_place_id: UUID,
        user: CurrentUser,
        purpose_tag_ids: list[int] | None,
        search_mode: str | None,
    ) -> dict:
        """STEP6 — 후보를 탐색해 recommendation_request/candidate 를 생성한다.

        경로 점수·이유·순위는 다루지 않는다. 이후 route-scores 엔드포인트가 이어받는다.
        """
        tp = self.repo.get_trip_place(trip_place_id)
        if tp is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정 장소를 찾을 수 없습니다.", 404)
        trip = self.repo.get_trip_owned(tp.trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.FORBIDDEN, "접근 권한이 없습니다.", 403)

        requested_mode = search_mode or "default"
        if requested_mode not in candidate_pipeline.RADIUS_KM_BY_MODE:
            raise AppError(
                ErrorCode.INVALID_SEARCH_MODE, "search_mode 값이 올바르지 않습니다.", 400
            )

        origin_coords = get_place_coords(self.db, tp.place_id)
        if origin_coords is None:
            raise AppError(
                ErrorCode.VALIDATION_ERROR, "원래 장소의 좌표 정보가 없습니다.", 422
            )
        origin_lat, origin_lng = origin_coords

        tag_code_map = self.repo.get_experience_tag_code_map()
        code_by_id = {tag_id: code for code, tag_id in tag_code_map.items()}
        purpose_tag_codes = [
            code_by_id[tag_id] for tag_id in (purpose_tag_ids or []) if tag_id in code_by_id
        ]

        duplicate_place_ids = self.repo.list_trip_place_ids(trip.id)
        duplicate_names = {
            place.name for place in self.repo.get_places_map(duplicate_place_ids).values()
        }

        experience_threshold = (
            candidate_pipeline.RELAXED_EXPERIENCE_THRESHOLD
            if requested_mode == "relaxed_experience"
            else candidate_pipeline.DEFAULT_EXPERIENCE_THRESHOLD
        )
        modes_to_try = (
            [requested_mode]
            if requested_mode != "default"
            else ["default", "expanded_radius"]
        )

        survivors: list[candidate_pipeline.EnrichedCandidate] = []
        excluded_count = 0
        final_mode = requested_mode
        for mode in modes_to_try:
            final_mode = mode
            radius_km = candidate_pipeline.RADIUS_KM_BY_MODE[mode]
            generated = candidate_pipeline.generate_candidates(
                origin_lat,
                origin_lng,
                radius_km,
                db_pool_fetcher=lambda radius_m: self.repo.list_nearby_recommendable_places(
                    origin_lat, origin_lng, radius_m, duplicate_place_ids
                ),
            )
            enriched = candidate_pipeline.enrich_candidates(
                generated,
                trip.travel_date,
                purpose_tag_codes,
                self.analysis_repo,
                self.places,
                self.repo,
                code_by_id,
            )
            survivors, excluded_count = candidate_pipeline.filter_candidates(
                enriched, duplicate_names, experience_threshold
            )
            if len(survivors) >= candidate_pipeline.MIN_CANDIDATES or mode == modes_to_try[-1]:
                break

        survivors = candidate_pipeline.select_top_candidates(
            survivors, candidate_pipeline.MAX_CANDIDATES
        )

        try:
            row_dicts = [self._materialize_candidate(c, tag_code_map) for c in survivors]
            status = "success" if row_dicts else "no_candidate"
            request = self.repo.create_request_with_candidates(
                trip_place_id, final_mode, status, row_dicts
            )
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AppError(
                ErrorCode.DB_ERROR, "추천 후보를 저장하는 중 오류가 발생했습니다.", 500
            ) from exc

        return {
            "requestId": str(request.id),
            "tripPlaceId": str(trip_place_id),
            "searchMode": final_mode,
            "status": status,
            "candidateCount": len(row_dicts),
            "excludedCount": excluded_count,
        }

    def _materialize_candidate(
        self, candidate: "candidate_pipeline.EnrichedCandidate", tag_code_map: dict[str, int]
    ) -> dict:
        """TourAPI 후보는 place 행을 확보하고 place_experience_tag(tour_category)도 채운다."""
        source = candidate.source
        if source.from_tour_api:
            place = self.places.get_or_create(
                source_type="tour_api",
                tour_content_id=source.id,
                name=source.name,
                longitude=source.longitude,
                latitude=source.latitude,
                address=source.address,
                area_cd=source.area_cd,
                signgu_cd=source.signgu_cd,
            )
            place_id = place.id
            weights = {
                tag_code_map[code]: weight
                for code, weight in candidate.category_weights.items()
                if code in tag_code_map
            }
            if weights:
                self.repo.upsert_place_experience_tags(
                    place_id, weights, source=candidate_pipeline.AUTO_CATEGORY_SOURCE
                )
        else:
            place_id = UUID(source.id)

        return {
            "candidate_place_id": place_id,
            "experience_score": Decimal(str(candidate.experience_score)),
            "congestion_level": candidate.congestion_level,
            "feasibility_status": "UNKNOWN",
        }

    def _assert_request_owned(self, request_id: UUID, user: CurrentUser):
        req = self.repo.get_request(request_id)
        if req is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "추천 요청을 찾을 수 없습니다.", 404)
        tp = self.repo.get_trip_place(req.trip_place_id)
        if tp is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정 장소를 찾을 수 없습니다.", 404)
        trip = self.repo.get_trip_owned(tp.trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.FORBIDDEN, "접근 권한이 없습니다.", 403)
        return req, tp, trip

    @staticmethod
    def _seconds_to_minutes(seconds: int | None) -> int | None:
        if seconds is None:
            return None
        return int(round(seconds / 60.0))

    def _adjacent_travel_seconds(
        self,
        prev_place_id: UUID | None,
        place_id: UUID,
        next_place_id: UUID | None,
        mode: str,
    ) -> int | None:
        if prev_place_id is None and next_place_id is None:
            return 0
        total = 0
        if prev_place_id is not None:
            leg = self.routes.get_leg(prev_place_id, place_id, mode)
            if leg is None:
                return None
            total += leg.duration_seconds
        if next_place_id is not None:
            leg = self.routes.get_leg(place_id, next_place_id, mode)
            if leg is None:
                return None
            total += leg.duration_seconds
        return total

    def score_routes(
        self,
        request_id: UUID,
        user: CurrentUser,
        transport_mode: str | None,
        extra_time_limit_minutes: int | None,
    ) -> dict:
        """후보별 거리/경로 점수만 계산해 저장·반환한다. 순위·totalScore는 다루지 않는다.

        `status`는 지금 "success"/"no_candidate" 둘뿐이지만, 프론트가 두 가지를 구분해서
        보여줘야 하므로("후보 없음"은 정상 결과, 그 외는 진짜 오류) 같은 문구·코드로 뭉뚱
        그리면 안 된다 — "no_candidate"만 따로 코드를 내려서, 나중에 "success"가 아닌
        다른 상태가 추가돼도(예: 생성 중 실패) 그게 조용히 "후보 없음"으로 오분류되지
        않게 한다(2026-09-18, 코드 리뷰로 발견).
        """
        req, tp, trip = self._assert_request_owned(request_id, user)
        if req.status == "no_candidate":
            raise AppError(
                ErrorCode.NO_CANDIDATE,
                "이 조건에 맞는 대안 후보를 찾지 못했습니다.",
                400,
            )
        if req.status != "success":
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "추천 요청이 아직 완료되지 않았습니다.",
                400,
            )

        # 요청 transport_mode override는 쓰지 않는다. get_candidates()가 trip 기준으로
        # travelMinutes를 다시 계산하므로, 점수와 표시 시각이 같은 교통수단이어야 한다.
        _ = transport_mode
        mode = trip.transport_mode or "walk"
        limit = (
            extra_time_limit_minutes
            if extra_time_limit_minutes is not None
            else trip.extra_time_limit_minutes
        )

        original_place = self.repo.get_place(tp.place_id)
        original_name = original_place.name if original_place else "원래 장소"
        prev_tp, next_tp = self.repo.neighbors(trip.id, tp.position)

        baseline_seconds = 0
        if prev_tp is not None:
            leg = self.routes.get_leg(prev_tp.place_id, tp.place_id, mode)
            if leg:
                baseline_seconds += leg.duration_seconds
        if next_tp is not None:
            leg = self.routes.get_leg(tp.place_id, next_tp.place_id, mode)
            if leg:
                baseline_seconds += leg.duration_seconds

        candidates = self.repo.list_candidates(request_id)
        scored: list[tuple] = []

        for cand in candidates:
            cand_place = self.repo.get_place(cand.candidate_place_id)
            cand_name = cand_place.name if cand_place else "후보"

            dist_prev = dist_next = None
            new_seconds = 0
            route_available = True
            is_estimated = False
            route_source = None

            if prev_tp is not None:
                leg = self.routes.get_leg(prev_tp.place_id, cand.candidate_place_id, mode)
                if leg is None:
                    route_available = False
                else:
                    dist_prev = leg.distance_m
                    new_seconds += leg.duration_seconds
                    is_estimated = is_estimated or leg.is_estimated
                    route_source = leg.route_source
            if next_tp is not None and route_available:
                leg = self.routes.get_leg(cand.candidate_place_id, next_tp.place_id, mode)
                if leg is None:
                    route_available = False
                else:
                    dist_next = leg.distance_m
                    new_seconds += leg.duration_seconds
                    is_estimated = is_estimated or leg.is_estimated
                    route_source = leg.route_source or route_source

            if prev_tp is None and next_tp is None:
                extra_minutes = 0
                travel_minutes = 0
                route_available = True
                route_source = route_source or "api"
            elif route_available:
                extra_minutes = max(0, int(round((new_seconds - baseline_seconds) / 60.0)))
                travel_minutes = int(round(new_seconds / 60.0))
            else:
                extra_minutes = None
                travel_minutes = None

            route_result = compute_route_score(
                extra_minutes=extra_minutes,
                limit_minutes=limit,
                feasibility_status=cand.feasibility_status,
                route_available=route_available,
            )
            reason = build_reason_text(
                original_name=original_name,
                candidate_name=cand_name,
                extra_minutes=extra_minutes,
                congestion_level=cand.congestion_level,
                experience_score=float(cand.experience_score),
            )
            now = datetime.now(timezone.utc)
            ranking = RecommendationRanking(
                candidate_id=cand.id,
                route_score=to_decimal(route_result.route_score),
                congestion_score=None,
                operation_score=None,
                total_score=None,
                rank=None,
                scored_at=now,
            )
            route = RecommendationRoute(
                candidate_id=cand.id,
                distance_prev_m=dist_prev,
                distance_next_m=dist_next,
                extra_minutes=extra_minutes,
                route_source=route_source,
                is_route_estimated=is_estimated,
                calculated_at=now,
            )
            reason_row = RecommendationReason(
                candidate_id=cand.id,
                recommend_reason=reason if route_result.is_eligible else None,
                not_recommend_reason=None if route_result.is_eligible else reason,
                reason_source_snapshot=route_result.snapshot,
                is_eligible=route_result.is_eligible,
                exclusion_reason=route_result.exclusion_reason,
            )
            saved_ranking = self.repo.upsert_ranking(ranking)
            saved_route = self.repo.upsert_route(route)
            saved_reason = self.repo.upsert_reason(reason_row)
            scored.append((cand, saved_ranking, saved_route, saved_reason, cand_name, travel_minutes))

        self.db.commit()

        candidates_out = [
            {
                "candidateId": str(c.id),
                "placeId": str(c.candidate_place_id),
                "placeName": name,
                "experienceScore": float(c.experience_score),
                "routeScore": float(r.route_score or 0),
                "extraMinutes": route.extra_minutes,
                "travelMinutes": travel,
                "distancePrevM": route.distance_prev_m,
                "distanceNextM": route.distance_next_m,
                "congestionLevel": c.congestion_level,
                "isRouteEstimated": route.is_route_estimated,
                "isEligible": reason.is_eligible,
                "exclusionReason": reason.exclusion_reason,
            }
            for c, r, route, reason, name, travel in scored
        ]
        return {
            "requestId": str(request_id),
            "scoredCount": len(candidates_out),
            "candidates": candidates_out,
        }

    def get_candidates(self, request_id: UUID, user: CurrentUser) -> dict:
        req, tp, trip = self._assert_request_owned(request_id, user)
        original = self.repo.get_place(tp.place_id)
        analysis = self.repo.latest_analysis(tp.id)
        original_level = analysis.level if analysis and analysis.level else "unknown"
        scored = self.repo.list_scored_for_request(request_id)
        if not scored:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "먼저 경로 점수 계산을 실행해 주세요.",
                400,
            )

        tags_map = self.repo.list_place_tags_map(
            [cand.candidate_place_id for cand, *_ in scored]
        )
        mode = trip.transport_mode or "walk"
        prev_tp, next_tp = self.repo.neighbors(trip.id, tp.position)
        prev_place_id = prev_tp.place_id if prev_tp is not None else None
        next_place_id = next_tp.place_id if next_tp is not None else None
        original_travel_minutes = self._seconds_to_minutes(
            self._adjacent_travel_seconds(prev_place_id, tp.place_id, next_place_id, mode)
        )
        candidates = []
        for cand, ranking, route, reason in scored:
            place = self.repo.get_place(cand.candidate_place_id)
            after = cand.congestion_level
            improvement = f"{original_level}_to_{after}"
            reason_text = None
            if reason is not None:
                reason_text = reason.recommend_reason or reason.not_recommend_reason
            travel_minutes = self._seconds_to_minutes(
                self._adjacent_travel_seconds(
                    prev_place_id, cand.candidate_place_id, next_place_id, mode
                )
            )
            candidates.append(
                {
                    "candidateId": str(cand.id),
                    "placeName": place.name if place else "",
                    "experienceScore": float(cand.experience_score),
                    "routeScore": float(ranking.route_score or 0),
                    "congestionLevel": after,
                    "congestionImprovement": improvement,
                    "extraMinutes": route.extra_minutes if route else None,
                    "travelMinutes": travel_minutes,
                    "distancePrevM": route.distance_prev_m if route else None,
                    "distanceNextM": route.distance_next_m if route else None,
                    "reasonText": reason_text,
                    "isEligible": reason.is_eligible if reason else False,
                    "exclusionReason": reason.exclusion_reason if reason else None,
                    "tags": tags_map.get(cand.candidate_place_id, []),
                    "address": place.address if place else None,
                }
            )

        return {
            "originalPlace": {
                "placeId": str(tp.place_id),
                "name": original.name if original else "",
                "congestionLevel": original_level,
                "travelMinutes": original_travel_minutes,
            },
            "candidates": candidates,
            "requestId": str(req.id),
            "tripPlaceId": str(tp.id),
        }

    def replacement_preview(
        self, trip_place_id: UUID, candidate_id: UUID, user: CurrentUser
    ) -> dict:
        tp = self.repo.get_trip_place(trip_place_id)
        if tp is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정 장소를 찾을 수 없습니다.", 404)
        trip = self.repo.get_trip_owned(tp.trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.FORBIDDEN, "접근 권한이 없습니다.", 403)

        cand = self.repo.get_candidate(candidate_id)
        if cand is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "후보를 찾을 수 없습니다.", 404)
        ranking = self.repo.get_ranking_by_candidate(candidate_id)
        reason = self.repo.get_reason_by_candidate(candidate_id)
        route = self.repo.get_route_by_candidate(candidate_id)
        if ranking is None or reason is None or not reason.is_eligible:
            raise AppError(ErrorCode.INVALID_REQUEST, "경로 점수가 없는 후보입니다.", 400)

        before_place = self.repo.get_place(tp.place_id)
        after_place = self.repo.get_place(cand.candidate_place_id)
        analysis = self.repo.latest_analysis(tp.id)
        before_level = analysis.level if analysis and analysis.level else "high"
        after_level = cand.congestion_level

        mode = trip.transport_mode or "walk"
        prev_tp, next_tp = self.repo.neighbors(trip.id, tp.position)
        before_sec = after_sec = 0
        if prev_tp:
            leg = self.routes.get_leg(prev_tp.place_id, tp.place_id, mode)
            if leg:
                before_sec += leg.duration_seconds
            leg = self.routes.get_leg(prev_tp.place_id, cand.candidate_place_id, mode)
            if leg:
                after_sec += leg.duration_seconds
        if next_tp:
            leg = self.routes.get_leg(tp.place_id, next_tp.place_id, mode)
            if leg:
                before_sec += leg.duration_seconds
            leg = self.routes.get_leg(cand.candidate_place_id, next_tp.place_id, mode)
            if leg:
                after_sec += leg.duration_seconds

        return {
            "before": {
                "placeId": str(tp.place_id),
                "name": before_place.name if before_place else "",
                "congestionLevel": before_level,
            },
            "after": {
                "placeId": str(cand.candidate_place_id),
                "name": after_place.name if after_place else "",
                "congestionLevel": after_level,
            },
            "extraMinutes": route.extra_minutes if route else None,
            "totalTravelBefore": int(round(before_sec / 60)),
            "totalTravelAfter": int(round(after_sec / 60)),
            "candidateId": str(candidate_id),
            "tripPlaceId": str(trip_place_id),
        }

    def apply_replacement(
        self, trip_place_id: UUID, candidate_id: UUID, user: CurrentUser
    ) -> dict:
        # 같은 trip_place에 대한 교체 적용/취소가 동시에 겹치지 않도록 첫 조회에서부터
        # 잠근다 — 아래 모든 검증·변경은 이 잠금 이후 값 기준이다. get_trip_place()로 먼저
        # 읽은 뒤 이 메서드를 또 부르면 identity map 때문에 잠금이 무의미해지므로, 이
        # trip_place에 대한 유일한 조회로 쓴다.
        tp = self.repo.get_trip_place_for_update(trip_place_id)
        if tp is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정 장소를 찾을 수 없습니다.", 404)
        trip = self.repo.get_trip_owned(tp.trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.FORBIDDEN, "접근 권한이 없습니다.", 403)
        if tp.is_fixed:
            raise AppError(ErrorCode.CONFLICT, "고정된 장소는 교체할 수 없습니다.", 409)

        # candidate_id가 실제로 이 trip_place의 추천 요청에서 나온 것인지까지 확인한다 —
        # id만으로 조회하면 다른 trip_place(다른 사용자 포함)의 candidate_id도 그대로
        # 통과해서 적용될 수 있었다.
        cand = self.repo.get_candidate_for_trip_place(candidate_id, tp.id)
        if cand is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "후보를 찾을 수 없습니다.", 404)
        ranking = self.repo.get_ranking_by_candidate(candidate_id)
        reason = self.repo.get_reason_by_candidate(candidate_id)
        route = self.repo.get_route_by_candidate(candidate_id)
        if ranking is None or reason is None or not reason.is_eligible:
            raise AppError(ErrorCode.INVALID_REQUEST, "경로 점수가 없는 후보입니다.", 400)
        # 이미 잠근 tp 기준으로 비교한다 — 현재 장소와 같은 장소로의 "교체"는 의미 없는
        # 이력만 쌓는다(교체 전/후가 동일).
        if cand.candidate_place_id == tp.place_id:
            raise AppError(ErrorCode.CONFLICT, "이미 적용된 장소입니다.", 409)

        from_place_id = tp.place_id
        to_place_id = cand.candidate_place_id
        if tp.initial_place_id is None:
            tp.initial_place_id = from_place_id

        analysis = self.repo.latest_analysis(tp.id)
        before_level = analysis.level if analysis else None
        reason_snapshot = reason.recommend_reason or reason.not_recommend_reason

        replacement = Replacement(
            trip_place_id=tp.id,
            from_place_id=from_place_id,
            to_place_id=to_place_id,
            ranking_id=ranking.id,
            reason_snapshot=reason_snapshot,
            extra_minutes=route.extra_minutes if route else None,
            before_level=before_level,
            after_level=cand.congestion_level,
            applied_at=datetime.now(timezone.utc),
        )
        self.repo.create_replacement(replacement)

        tp.place_id = to_place_id
        tp.resolution_status = "replaced"
        # 이 trip_place에 붙어 있던 옛 장소의 분석 결과를 지운다 — 안 지우면 다음 조회 때
        # 새 장소인데 옛 장소의 혼잡도가 그대로 보인다. place_concentration_mapping은 place_id
        # 기준 재사용 데이터라 여기서 지우지 않는다(analysis_repository.clear_analysis_for_trip_place 참고).
        # 후보에 이미 계산된 혼잡도가 있으면 그 장소만 다시 채워, 다른 장소 분석을 건드리지 않는다.
        # 아래 self.db.commit() 하나로 이 메서드의 모든 변경이 같은 트랜잭션에 묶인다.
        self.analysis_repo.clear_analysis_for_trip_place(tp.id)
        if cand.congestion_level in (
            ConcentrationLevel.LOW,
            ConcentrationLevel.MID,
            ConcentrationLevel.HIGH,
        ):
            self.analysis_repo.write_analysis(
                tp.id,
                AnalysisStatus.SUCCESS,
                cand.congestion_level,
                None,
                RULE_VERSION,
            )

        self.repo.log_interaction(
            user_id=user.id,
            trip_id=trip.id,
            trip_place_id=tp.id,
            event_type="replacement_apply",
            ranking_id=ranking.id,
        )
        self.db.commit()

        return {
            "replacementId": str(replacement.id),
            "tripPlaceId": str(tp.id),
            "fromPlaceId": str(from_place_id),
            "toPlaceId": str(to_place_id),
            "resolutionStatus": "replaced",
            "appliedAt": replacement.applied_at.isoformat(),
        }

    def revert_replacement(self, replacement_id: UUID, user: CurrentUser) -> dict:
        replacement = self.repo.get_replacement(replacement_id)
        if replacement is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "교체 이력을 찾을 수 없습니다.", 404)

        # apply_replacement()와 동일하게, 이 trip_place에 대한 유일한 조회로 잠근다.
        tp = self.repo.get_trip_place_for_update(replacement.trip_place_id)
        if tp is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정 장소를 찾을 수 없습니다.", 404)
        trip = self.repo.get_trip_owned(tp.trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.FORBIDDEN, "접근 권한이 없습니다.", 403)

        if replacement.reverted_at is not None:
            raise AppError(ErrorCode.CONFLICT, "이미 되돌린 교체입니다.", 409)

        # place_id 비교만으로는 "최신 교체"를 판별할 수 없다 — A→B→C→B처럼 같은 장소로
        # 되돌아오는 이력이면 오래된 교체(A→B)도 현재 place_id와 같아서 통과해버린다.
        # 이 trip_place에서 아직 안 되돌린 가장 최근 교체인지 직접 조회해서만 취소를
        # 허용한다. 위에서 이미 trip_place를 잠근 뒤라 이 조회도 잠금 이후 상태를 본다.
        active = self.repo.active_replacement(tp.id)
        if active is None or active.id != replacement.id:
            raise AppError(
                ErrorCode.CONFLICT,
                "이후에 다른 교체가 적용되어 이 교체를 되돌릴 수 없습니다.",
                409,
            )

        now = datetime.now(timezone.utc)
        replacement.reverted_at = now
        tp.place_id = replacement.from_place_id
        # 아래 active_replacement() 재조회가 방금 바꾼 reverted_at을 보게 flush한다
        # (세션이 autoflush=False라 명시적으로 안 하면 옛 값을 기준으로 조회될 수 있음).
        self.db.flush()

        # 되돌린 뒤에도 이 trip_place에 아직 안 되돌린 더 오래된 교체가 남아있으면(예:
        # A→B→C에서 C→B만 되돌린 경우) "replaced" 상태를 유지한다 — 무조건 "pending"으로
        # 초기화하면 아직 유효한 이전 교체 이력과 화면 상태가 어긋난다.
        remaining = self.repo.active_replacement(tp.id)
        tp.resolution_status = "replaced" if remaining is not None else "pending"

        # apply_replacement()와 같은 이유로, 되돌린 장소 기준 분석 결과가 없으면 이전(옛)
        # 장소의 분석값이 그대로 남아 잘못 보일 수 있다.
        self.analysis_repo.clear_analysis_for_trip_place(tp.id)

        self.repo.log_interaction(
            user_id=user.id,
            trip_id=trip.id,
            trip_place_id=tp.id,
            event_type="replacement_revert",
            ranking_id=replacement.ranking_id,
        )
        self.db.commit()

        return {
            "replacementId": str(replacement.id),
            "tripPlaceId": str(tp.id),
            "resolutionStatus": tp.resolution_status,
            "revertedAt": now.isoformat(),
        }

    def remaining_congested(self, trip_id: UUID, user: CurrentUser) -> dict:
        trip = self.repo.get_trip_owned(trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정을 찾을 수 없습니다.", 404)
        items_raw = self.repo.remaining_congested(trip_id)
        items = []
        for tp, analysis in items_raw:
            place = self.repo.get_place(tp.place_id)
            items.append(
                {
                    "tripPlaceId": str(tp.id),
                    "placeName": place.name if place else "",
                    "level": analysis.level if analysis else "high",
                }
            )
        return {
            "tripId": str(trip_id),
            "remainingCount": len(items),
            "items": items,
            "allResolved": len(items) == 0,
        }

    def confirm(self, trip_id: UUID, user: CurrentUser) -> dict:
        trip = self.repo.get_trip_owned(trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정을 찾을 수 없습니다.", 404)
        now = datetime.now(timezone.utc)
        trip.status = "confirmed"
        trip.confirmed_at = now
        if trip.trip_places:
            self.repo.log_interaction(
                user_id=user.id,
                trip_id=trip.id,
                trip_place_id=trip.trip_places[0].id,
                event_type="trip_confirm",
            )
        self.db.commit()
        return {
            "tripId": str(trip.id),
            "status": "confirmed",
            "confirmedAt": now.isoformat(),
        }

    def build_guide(self, trip: Trip) -> dict:
        places_sorted = sorted(trip.trip_places, key=lambda p: p.position)
        mode = trip.transport_mode or "walk"

        # 정류장마다 get_place()/active_replacement()를 반복 호출하면(가이드북 정류장
        # 최대 수십 개) 그만큼 DB 왕복이 났다 — 필요한 걸 먼저 한 번에 모아서 조회한다.
        replacements = self.repo.active_replacements_map([tp.id for tp in places_sorted])

        place_ids: set[UUID] = set()
        for tp in places_sorted:
            place_ids.add(tp.place_id)
            active = replacements.get(tp.id)
            if active:
                place_ids.add(active.from_place_id)
            elif tp.initial_place_id and tp.initial_place_id != tp.place_id:
                place_ids.add(tp.initial_place_id)
        places_by_id = self.places.get_by_ids(list(place_ids))

        leg_pairs = [
            (places_sorted[i].place_id, places_sorted[i + 1].place_id)
            for i in range(len(places_sorted) - 1)
        ]
        legs = self.routes.get_legs(leg_pairs, mode)

        stops = []
        for i, tp in enumerate(places_sorted):
            place = places_by_id.get(tp.place_id)
            active = replacements.get(tp.id)
            travel_to_next = None
            if i + 1 < len(places_sorted):
                nxt = places_sorted[i + 1]
                leg = legs.get((tp.place_id, nxt.place_id))
                if leg:
                    travel_to_next = {
                        "distanceM": leg.distance_m,
                        "durationMin": int(round(leg.duration_seconds / 60)),
                    }
            replaced_from = None
            replace_reason = None
            extra_minutes = None
            before_level = None
            after_level = None
            if active:
                from_place = places_by_id.get(active.from_place_id)
                replaced_from = from_place.name if from_place else None
                replace_reason = active.reason_snapshot
                extra_minutes = active.extra_minutes
                before_level = active.before_level
                after_level = active.after_level
            elif tp.initial_place_id and tp.initial_place_id != tp.place_id:
                from_place = places_by_id.get(tp.initial_place_id)
                replaced_from = from_place.name if from_place else None
                replace_reason = "혼잡 개선 및 유사 경험 제공"

            visit = tp.visit_time.strftime("%H:%M") if tp.visit_time else None
            place_name = place.name if place else ""
            stops.append(
                {
                    "position": tp.position,
                    "placeName": place_name,
                    "visitTime": visit,
                    "stayMinutes": tp.stay_minutes,
                    "wasReplaced": replaced_from is not None,
                    "replacedFrom": replaced_from,
                    "replaceReason": replace_reason,
                    "extraMinutes": extra_minutes,
                    "beforeLevel": before_level,
                    "afterLevel": after_level,
                    "travelToNext": travel_to_next,
                    "imageUrl": self._resolve_stop_image(place),
                }
            )

        entries = self.repo.guide_entries(trip.id)
        ugc = [
            {
                "content": e.content,
                "imageUrl": e.image_url,
                "displayOrder": e.display_order,
            }
            for e in entries
            if e.content or e.image_url
        ]
        memo_entry = next(
            (e for e in entries if getattr(e, "trip_place_id", None) is None),
            None,
        )
        memo = memo_entry.content if memo_entry is not None else None
        if memo is None:
            memo = next((e.content for e in entries if e.content), None)

        cover_image_url = next((e.image_url for e in entries if e.image_url), None)
        region = getattr(trip, "region", None)
        region_name = region.name if region is not None else None
        city_name = short_city_name(region_name)
        district_name = majority_district(
            [getattr(places_by_id.get(tp.place_id), "address", None) for tp in places_sorted]
        ) or district_from_text(region_name)

        if not cover_image_url:
            fetched_cover = photo_gallery.pick_cover_image(city_name, district_name)
            if fetched_cover:
                cover_image_url = fetched_cover
                self.repo.cache_cover_image(trip.id, fetched_cover)
                self.db.commit()

        total_travel_min = sum(
            (stop["travelToNext"]["durationMin"] if stop["travelToNext"] else 0)
            for stop in stops
        )
        tags = self.repo.trip_tag_names(trip.id)
        if not isinstance(tags, list):
            tags = []

        share_link = self.repo.get_active_share_link(trip.id)
        visibility = (
            share_link.visibility
            if share_link is not None
            else ShareLinkVisibility.LINK
        )

        return {
            "tripId": str(trip.id),
            "title": trip.title,
            "travelDate": trip.travel_date.isoformat() if trip.travel_date else None,
            "regionName": region_name,
            "cityName": city_name,
            "districtName": district_name,
            "totalTravelMin": total_travel_min,
            "tags": tags,
            "memo": memo,
            "status": trip.status,
            "coverImageUrl": cover_image_url,
            "stops": stops,
            "entries": ugc,
            "visibility": visibility,
            "shareToken": share_link.token if share_link is not None else None,
        }

    def _resolve_stop_image(self, place) -> str | None:
        """장소 썸네일: TourAPI firstimage → 관광사진 키워드. 없으면 None."""
        if place is None:
            return None
        content_id = getattr(place, "tour_content_id", None)
        if content_id:
            url = tour_api.fetch_place_image(str(content_id))
            if url:
                return url
        name = getattr(place, "name", None)
        if name:
            return photo_gallery.first_image_for_place(str(name))
        return None

    def update_guide_memo(self, trip_id: UUID, user: CurrentUser, content: str | None) -> dict:
        trip = self.repo.get_trip_owned(trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정을 찾을 수 없습니다.", 404)
        if trip.status != "confirmed":
            raise AppError(ErrorCode.CONFLICT, "확정된 일정만 메모를 저장할 수 있습니다.", 409)
        text = content.strip() if isinstance(content, str) else None
        if not text:
            text = None
        self.repo.upsert_trip_memo(trip.id, text)
        self.db.commit()
        return {"memo": text}

    def get_guide(self, trip_id: UUID, user: CurrentUser) -> dict:
        trip = self.repo.get_trip_owned(trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정을 찾을 수 없습니다.", 404)
        return self.build_guide(trip)

    def create_share_link(
        self, trip_id: UUID, user: CurrentUser, visibility: str | None
    ) -> dict:
        trip = self.repo.get_trip_owned(trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정을 찾을 수 없습니다.", 404)
        if trip.status != "confirmed":
            raise AppError(ErrorCode.CONFLICT, "확정된 일정만 공유할 수 있습니다.", 409)
        if visibility is not None and visibility not in ShareLinkVisibility.ALL:
            raise AppError(
                ErrorCode.INVALID_REQUEST, "허용되지 않은 공개 범위입니다.", 400
            )

        self.repo.lock_trip(trip.id)
        link = self.repo.get_active_share_link(trip.id)
        if link is None:
            token = secrets.token_urlsafe(12)
            link = ShareLink(
                trip_id=trip.id,
                token=token,
                visibility=visibility or ShareLinkVisibility.LINK,
                created_at=datetime.now(timezone.utc),
            )
            self.repo.create_share_link(link)
        elif visibility is not None:
            link.visibility = visibility

        self.db.commit()
        path = f"/guide/{link.token}"
        return {
            "token": link.token,
            "url": path,
            "absoluteUrl": f"{settings.FRONTEND_PUBLIC_ORIGIN.rstrip('/')}{path}",
            "expiresAt": link.expires_at.isoformat() if link.expires_at else None,
        }

    def get_guide_by_token(self, token: str) -> dict:
        link = self.repo.get_share_by_token(token)
        if link is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "공유 링크를 찾을 수 없습니다.", 404)
        now = datetime.now(timezone.utc)
        if link.revoked_at is not None or (
            link.expires_at is not None and link.expires_at <= now
        ):
            raise AppError(ErrorCode.SHARE_LINK_GONE, "만료되었거나 취소된 링크입니다.", 410)
        trip = self.repo.get_trip(link.trip_id)
        if trip is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정을 찾을 수 없습니다.", 404)
        return self.build_guide(trip)
