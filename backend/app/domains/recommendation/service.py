"""추천 경로 점수·교체·확정·가이드 서비스."""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.db.models.recommendation import (
    RecommendationRanking,
    RecommendationReason,
    RecommendationRoute,
)
from app.db.models.replacement import Replacement
from app.db.models.share_link import ShareLink
from app.db.models.trip import Trip
from app.domains.recommendation.route import RouteService
from app.domains.recommendation.scoring import (
    build_reason_text,
    compute_route_score,
    to_decimal,
)
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.user import CurrentUser


class RecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RecommendationRepository(db)
        self.routes = RouteService(db)

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

    def score_routes(
        self,
        request_id: UUID,
        user: CurrentUser,
        transport_mode: str | None,
        extra_time_limit_minutes: int | None,
    ) -> dict:
        """후보별 거리/경로 점수만 계산해 저장·반환한다. 순위·totalScore는 다루지 않는다."""
        req, tp, trip = self._assert_request_owned(request_id, user)
        if req.status != "success":
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "추천 요청이 아직 완료되지 않았습니다.",
                400,
            )

        mode = transport_mode or trip.transport_mode or "walk"
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
                route_available = True
                route_source = route_source or "api"
            elif route_available:
                extra_minutes = max(0, int(round((new_seconds - baseline_seconds) / 60.0)))
            else:
                extra_minutes = None

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
            scored.append((cand, saved_ranking, saved_route, saved_reason, cand_name))

        self.db.commit()

        candidates_out = [
            {
                "candidateId": str(c.id),
                "placeId": str(c.candidate_place_id),
                "placeName": name,
                "experienceScore": float(c.experience_score),
                "routeScore": float(r.route_score or 0),
                "extraMinutes": route.extra_minutes,
                "distancePrevM": route.distance_prev_m,
                "distanceNextM": route.distance_next_m,
                "congestionLevel": c.congestion_level,
                "isRouteEstimated": route.is_route_estimated,
                "isEligible": reason.is_eligible,
                "exclusionReason": reason.exclusion_reason,
            }
            for c, r, route, reason, name in scored
        ]
        return {
            "requestId": str(request_id),
            "scoredCount": len(candidates_out),
            "candidates": candidates_out,
        }

    def get_candidates(self, request_id: UUID, user: CurrentUser) -> dict:
        req, tp, _trip = self._assert_request_owned(request_id, user)
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

        candidates = []
        for cand, ranking, route, reason in scored:
            place = self.repo.get_place(cand.candidate_place_id)
            after = cand.congestion_level
            improvement = f"{original_level}_to_{after}"
            reason_text = None
            if reason is not None:
                reason_text = reason.recommend_reason or reason.not_recommend_reason
            candidates.append(
                {
                    "candidateId": str(cand.id),
                    "placeName": place.name if place else "",
                    "experienceScore": float(cand.experience_score),
                    "routeScore": float(ranking.route_score or 0),
                    "congestionLevel": after,
                    "congestionImprovement": improvement,
                    "extraMinutes": route.extra_minutes if route else None,
                    "distancePrevM": route.distance_prev_m if route else None,
                    "distanceNextM": route.distance_next_m if route else None,
                    "reasonText": reason_text,
                    "isEligible": reason.is_eligible if reason else False,
                    "exclusionReason": reason.exclusion_reason if reason else None,
                }
            )

        return {
            "originalPlace": {
                "placeId": str(tp.place_id),
                "name": original.name if original else "",
                "congestionLevel": original_level,
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
        tp = self.repo.get_trip_place(trip_place_id)
        if tp is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정 장소를 찾을 수 없습니다.", 404)
        trip = self.repo.get_trip_owned(tp.trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.FORBIDDEN, "접근 권한이 없습니다.", 403)
        if tp.is_fixed:
            raise AppError(ErrorCode.CONFLICT, "고정된 장소는 교체할 수 없습니다.", 409)

        cand = self.repo.get_candidate(candidate_id)
        if cand is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "후보를 찾을 수 없습니다.", 404)
        ranking = self.repo.get_ranking_by_candidate(candidate_id)
        reason = self.repo.get_reason_by_candidate(candidate_id)
        route = self.repo.get_route_by_candidate(candidate_id)
        if ranking is None or reason is None or not reason.is_eligible:
            raise AppError(ErrorCode.INVALID_REQUEST, "경로 점수가 없는 후보입니다.", 400)

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
        if replacement.reverted_at is not None:
            raise AppError(ErrorCode.CONFLICT, "이미 되돌린 교체입니다.", 409)

        tp = self.repo.get_trip_place(replacement.trip_place_id)
        if tp is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정 장소를 찾을 수 없습니다.", 404)
        trip = self.repo.get_trip_owned(tp.trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.FORBIDDEN, "접근 권한이 없습니다.", 403)

        now = datetime.now(timezone.utc)
        replacement.reverted_at = now
        tp.place_id = replacement.from_place_id
        tp.resolution_status = "pending"

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
            "resolutionStatus": "pending",
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
        remaining = self.repo.remaining_congested(trip_id)
        if remaining:
            raise AppError(
                ErrorCode.UNRESOLVED_CONGESTED_PLACES,
                "아직 해결되지 않은 혼잡 장소가 있습니다.",
                409,
                extra={"pendingCount": len(remaining)},
            )
        now = datetime.now(timezone.utc)
        trip.status = "confirmed"
        trip.confirmed_at = now
        if trip.places:
            self.repo.log_interaction(
                user_id=user.id,
                trip_id=trip.id,
                trip_place_id=trip.places[0].id,
                event_type="trip_confirm",
            )
        self.db.commit()
        return {
            "tripId": str(trip.id),
            "status": "confirmed",
            "confirmedAt": now.isoformat(),
        }

    def build_guide(self, trip: Trip) -> dict:
        stops = []
        places_sorted = sorted(trip.places, key=lambda p: p.position)
        mode = trip.transport_mode or "walk"
        for i, tp in enumerate(places_sorted):
            place = self.repo.get_place(tp.place_id)
            active = self.repo.active_replacement(tp.id)
            travel_to_next = None
            if i + 1 < len(places_sorted):
                nxt = places_sorted[i + 1]
                leg = self.routes.get_leg(tp.place_id, nxt.place_id, mode)
                if leg:
                    travel_to_next = {
                        "distanceM": leg.distance_m,
                        "durationMin": int(round(leg.duration_seconds / 60)),
                    }
            replaced_from = None
            replace_reason = None
            if active:
                from_place = self.repo.get_place(active.from_place_id)
                replaced_from = from_place.name if from_place else None
                replace_reason = active.reason_snapshot
            elif tp.initial_place_id and tp.initial_place_id != tp.place_id:
                from_place = self.repo.get_place(tp.initial_place_id)
                replaced_from = from_place.name if from_place else None
                replace_reason = "혼잡 개선 및 유사 경험 제공"

            visit = tp.visit_time.strftime("%H:%M") if tp.visit_time else None
            stops.append(
                {
                    "position": tp.position,
                    "placeName": place.name if place else "",
                    "visitTime": visit,
                    "wasReplaced": replaced_from is not None,
                    "replacedFrom": replaced_from,
                    "replaceReason": replace_reason,
                    "travelToNext": travel_to_next,
                }
            )

        ugc = [
            {
                "content": e.content,
                "imageUrl": e.image_url,
                "displayOrder": e.display_order,
            }
            for e in self.repo.guide_entries(trip.id)
            if e.content or e.image_url
        ]

        return {
            "tripId": str(trip.id),
            "title": trip.title,
            "travelDate": trip.travel_date.isoformat() if trip.travel_date else None,
            "status": trip.status,
            "stops": stops,
            "entries": ugc,
        }

    def get_guide(self, trip_id: UUID, user: CurrentUser) -> dict:
        trip = self.repo.get_trip_owned(trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정을 찾을 수 없습니다.", 404)
        return self.build_guide(trip)

    def create_share_link(self, trip_id: UUID, user: CurrentUser, visibility: str) -> dict:
        trip = self.repo.get_trip_owned(trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정을 찾을 수 없습니다.", 404)
        if trip.status != "confirmed":
            raise AppError(ErrorCode.CONFLICT, "확정된 일정만 공유할 수 있습니다.", 409)
        token = secrets.token_urlsafe(12)
        link = ShareLink(
            trip_id=trip.id,
            token=token,
            visibility=visibility or "link",
            created_at=datetime.now(timezone.utc),
        )
        self.repo.create_share_link(link)
        self.db.commit()
        path = f"/guide/{token}"
        return {
            "token": token,
            "url": path,
            "absoluteUrl": f"{settings.FRONTEND_PUBLIC_ORIGIN.rstrip('/')}{path}",
            "expiresAt": None,
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
