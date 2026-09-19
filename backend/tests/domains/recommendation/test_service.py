"""RecommendationService 동작 검증 (DB/Kakao mock)."""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.clients.kakao_mobility import RouteResult
from app.core.exceptions import AppError, ErrorCode
from app.domains.recommendation.service import RecommendationService
from app.schemas.user import CurrentUser


def _user() -> CurrentUser:
    return CurrentUser(id=uuid4(), email="t@example.com", nickname="테스터", profile_image_url=None)


def test_confirm_succeeds_when_pending_congested():
    db = MagicMock()
    svc = RecommendationService(db)
    trip_id = uuid4()
    user = _user()
    trip = SimpleNamespace(
        id=trip_id,
        user_id=user.id,
        trip_places=[SimpleNamespace(id=uuid4())],
        status="draft",
        confirmed_at=None,
    )

    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.remaining_congested = MagicMock(
        return_value=[(SimpleNamespace(id=uuid4()), SimpleNamespace(level="high"))]
    )
    svc.repo.log_interaction = MagicMock()

    result = svc.confirm(trip_id, user)

    assert result["status"] == "confirmed"
    assert trip.status == "confirmed"
    assert trip.confirmed_at is not None
    db.commit.assert_called_once()
    svc.repo.log_interaction.assert_called_once()


def test_get_candidates_requires_prior_scoring():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    request_id = uuid4()
    trip_place_id = uuid4()
    trip_id = uuid4()

    req = SimpleNamespace(id=request_id, trip_place_id=trip_place_id, status="success")
    tp = SimpleNamespace(id=trip_place_id, trip_id=trip_id, place_id=uuid4())
    trip = SimpleNamespace(id=trip_id, user_id=user.id)

    svc.repo.get_request = MagicMock(return_value=req)
    svc.repo.get_trip_place = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_place = MagicMock(return_value=SimpleNamespace(name="경복궁"))
    svc.repo.latest_analysis = MagicMock(return_value=None)
    svc.repo.list_scored_for_request = MagicMock(return_value=[])

    with pytest.raises(AppError) as exc:
        svc.get_candidates(request_id, user)

    assert exc.value.status_code == 400
    assert "경로 점수" in exc.value.message


def test_get_candidates_includes_tags_and_address():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    request_id = uuid4()
    trip_place_id = uuid4()
    trip_id = uuid4()
    cand_place_id = uuid4()
    candidate_id = uuid4()

    req = SimpleNamespace(id=request_id, trip_place_id=trip_place_id, status="success")
    tp = SimpleNamespace(id=trip_place_id, trip_id=trip_id, place_id=uuid4(), position=1)
    trip = SimpleNamespace(id=trip_id, user_id=user.id, transport_mode="walk")
    cand = SimpleNamespace(
        id=candidate_id,
        candidate_place_id=cand_place_id,
        experience_score=Decimal("0.8000"),
        congestion_level="low",
    )
    ranking = SimpleNamespace(route_score=Decimal("0.7000"))
    route = SimpleNamespace(extra_minutes=12, distance_prev_m=2400, distance_next_m=3100)
    reason = SimpleNamespace(
        recommend_reason="기존 방문 목적과 유사해요",
        not_recommend_reason=None,
        is_eligible=True,
        exclusion_reason=None,
    )

    svc.repo.get_request = MagicMock(return_value=req)
    svc.repo.get_trip_place = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_place = MagicMock(
        side_effect=lambda pid: SimpleNamespace(
            name="서울한방진흥센터" if pid == cand_place_id else "경복궁",
            address="서울 동대문구 약령시로 21" if pid == cand_place_id else None,
        )
    )
    svc.repo.latest_analysis = MagicMock(return_value=SimpleNamespace(level="high"))
    svc.repo.list_scored_for_request = MagicMock(return_value=[(cand, ranking, route, reason)])
    svc.repo.list_place_tags_map = MagicMock(
        return_value={cand_place_id: [{"id": 2, "name": "역사·문화"}, {"id": 4, "name": "사진·전망"}]}
    )
    svc.repo.neighbors = MagicMock(return_value=(None, None))

    result = svc.get_candidates(request_id, user)

    assert result["originalPlace"]["name"] == "경복궁"
    assert result["originalPlace"]["travelMinutes"] == 0
    assert result["candidates"][0]["travelMinutes"] == 0
    assert result["candidates"][0]["address"] == "서울 동대문구 약령시로 21"
    assert result["candidates"][0]["tags"] == [
        {"id": 2, "name": "역사·문화"},
        {"id": 4, "name": "사진·전망"},
    ]
    svc.repo.list_place_tags_map.assert_called_once()


def test_score_routes_no_candidate_status_raises_distinct_error_code():
    """status가 "no_candidate"면 "요청 미완료"와 구분되는 전용 코드를 내려야 한다 — 프론트가
    문자열 매칭이 아니라 이 코드로 "후보 없음"(정상 결과)과 진짜 오류를 구분한다
    (2026-09-18, 코드 리뷰로 발견: req.status != "success" 하나로만 묶으면 나중에 "success"도
    "no_candidate"도 아닌 다른 상태가 추가돼도 같은 문구로 뭉뚱그려질 위험이 있었음)."""
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    request_id = uuid4()
    trip_place_id = uuid4()
    trip_id = uuid4()

    req = SimpleNamespace(id=request_id, trip_place_id=trip_place_id, status="no_candidate")
    tp = SimpleNamespace(id=trip_place_id, trip_id=trip_id, place_id=uuid4())
    trip = SimpleNamespace(id=trip_id, user_id=user.id)

    svc.repo.get_request = MagicMock(return_value=req)
    svc.repo.get_trip_place = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)

    with pytest.raises(AppError) as exc:
        svc.score_routes(request_id, user, None, None)

    assert exc.value.code == ErrorCode.NO_CANDIDATE
    assert exc.value.status_code == 400


def test_score_routes_other_non_success_status_keeps_generic_not_completed_error():
    """"success"도 "no_candidate"도 아닌(지금은 존재하지 않지만 향후 추가될 수 있는) 상태는
    "no_candidate" 전용 코드로 오분류되지 않고 기존 일반 코드를 유지해야 한다."""
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    request_id = uuid4()
    trip_place_id = uuid4()
    trip_id = uuid4()

    req = SimpleNamespace(id=request_id, trip_place_id=trip_place_id, status="pending")
    tp = SimpleNamespace(id=trip_place_id, trip_id=trip_id, place_id=uuid4())
    trip = SimpleNamespace(id=trip_id, user_id=user.id)

    svc.repo.get_request = MagicMock(return_value=req)
    svc.repo.get_trip_place = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)

    with pytest.raises(AppError) as exc:
        svc.score_routes(request_id, user, None, None)

    assert exc.value.code == ErrorCode.INVALID_REQUEST
    assert exc.value.code != ErrorCode.NO_CANDIDATE
    assert exc.value.status_code == 400


def test_score_routes_returns_route_score_without_rank_or_total():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    request_id = uuid4()
    trip_place_id = uuid4()
    trip_id = uuid4()
    place_id = uuid4()
    candidate_id = uuid4()
    cand_place_id = uuid4()

    req = SimpleNamespace(id=request_id, trip_place_id=trip_place_id, status="success")
    tp = SimpleNamespace(
        id=trip_place_id,
        trip_id=trip_id,
        place_id=place_id,
        position=2,
    )
    trip = SimpleNamespace(
        id=trip_id,
        user_id=user.id,
        transport_mode="walk",
        extra_time_limit_minutes=30,
    )
    cand = SimpleNamespace(
        id=candidate_id,
        candidate_place_id=cand_place_id,
        experience_score=Decimal("0.9000"),
        congestion_level="low",
        feasibility_status="OPEN_CONFIRMED",
    )

    saved_ranking = SimpleNamespace(
        route_score=Decimal("0.8500"),
        total_score=None,
        rank=None,
    )
    saved_route = SimpleNamespace(
        extra_minutes=5,
        distance_prev_m=100,
        distance_next_m=200,
        is_route_estimated=True,
    )
    saved_reason = SimpleNamespace(
        is_eligible=True,
        exclusion_reason=None,
    )

    svc.repo.get_request = MagicMock(return_value=req)
    svc.repo.get_trip_place = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_place = MagicMock(
        side_effect=lambda pid: SimpleNamespace(
            name="창덕궁" if pid == cand_place_id else "경복궁"
        )
    )
    svc.repo.neighbors = MagicMock(return_value=(None, None))
    svc.repo.list_candidates = MagicMock(return_value=[cand])
    svc.repo.upsert_ranking = MagicMock(return_value=saved_ranking)
    svc.repo.upsert_route = MagicMock(return_value=saved_route)
    svc.repo.upsert_reason = MagicMock(return_value=saved_reason)

    with patch(
        "app.domains.recommendation.service.RecommendationRanking",
        return_value=SimpleNamespace(),
    ), patch(
        "app.domains.recommendation.service.RecommendationRoute",
        return_value=SimpleNamespace(),
    ), patch(
        "app.domains.recommendation.service.RecommendationReason",
        return_value=SimpleNamespace(),
    ), patch.object(svc.routes, "get_leg") as get_leg:
        get_leg.return_value = RouteResult(
            distance_m=120,
            duration_seconds=300,
            provider="haversine",
            is_estimated=True,
            route_source="fallback_haversine",
        )
        result = svc.score_routes(request_id, user, None, None)

    assert result["scoredCount"] == 1
    item = result["candidates"][0]
    assert "routeScore" in item
    assert "totalScore" not in item
    assert "rank" not in item
    assert item["isEligible"] is True
    assert item["travelMinutes"] == 0
    db.commit.assert_called()


def test_score_routes_uses_trip_transport_mode_not_request_override():
    """요청의 car override는 무시하고 일정 기본값(walk)으로 경로를 계산한다."""
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    request_id = uuid4()
    trip_place_id = uuid4()
    trip_id = uuid4()
    place_id = uuid4()
    candidate_id = uuid4()
    cand_place_id = uuid4()
    prev_place_id = uuid4()
    next_place_id = uuid4()

    req = SimpleNamespace(id=request_id, trip_place_id=trip_place_id, status="success")
    tp = SimpleNamespace(
        id=trip_place_id,
        trip_id=trip_id,
        place_id=place_id,
        position=2,
    )
    trip = SimpleNamespace(
        id=trip_id,
        user_id=user.id,
        transport_mode="walk",
        extra_time_limit_minutes=30,
    )
    cand = SimpleNamespace(
        id=candidate_id,
        candidate_place_id=cand_place_id,
        experience_score=Decimal("0.9000"),
        congestion_level="low",
        feasibility_status="OPEN_CONFIRMED",
    )
    prev_tp = SimpleNamespace(place_id=prev_place_id)
    next_tp = SimpleNamespace(place_id=next_place_id)

    svc.repo.get_request = MagicMock(return_value=req)
    svc.repo.get_trip_place = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_place = MagicMock(
        side_effect=lambda pid: SimpleNamespace(
            name="창덕궁" if pid == cand_place_id else "경복궁"
        )
    )
    svc.repo.neighbors = MagicMock(return_value=(prev_tp, next_tp))
    svc.repo.list_candidates = MagicMock(return_value=[cand])
    svc.repo.upsert_ranking = MagicMock(
        return_value=SimpleNamespace(route_score=Decimal("0.8500"), total_score=None, rank=None)
    )
    svc.repo.upsert_route = MagicMock(
        return_value=SimpleNamespace(
            extra_minutes=5, distance_prev_m=100, distance_next_m=200, is_route_estimated=True,
        )
    )
    svc.repo.upsert_reason = MagicMock(
        return_value=SimpleNamespace(is_eligible=True, exclusion_reason=None)
    )

    with patch(
        "app.domains.recommendation.service.RecommendationRanking",
        return_value=SimpleNamespace(),
    ), patch(
        "app.domains.recommendation.service.RecommendationRoute",
        return_value=SimpleNamespace(),
    ), patch(
        "app.domains.recommendation.service.RecommendationReason",
        return_value=SimpleNamespace(),
    ), patch.object(svc.routes, "get_leg") as get_leg:
        get_leg.return_value = RouteResult(
            distance_m=120,
            duration_seconds=300,
            provider="haversine",
            is_estimated=True,
            route_source="fallback_haversine",
        )
        svc.score_routes(request_id, user, "car", None)

    modes = {call.args[2] for call in get_leg.call_args_list}
    assert modes == {"walk"}


def test_apply_replacement_clears_old_analysis_in_same_commit():
    """교체 후 옛 장소의 trip_place_analysis가 지워져야 새 장소 조회 시 옛 혼잡도가 안 남는다.

    clear → 새 혼잡도 write 가 별도 commit 없이 flush만 하고, apply_replacement의
    마지막 self.db.commit() 하나로 place_id 변경/분석 교체/interaction 기록이 함께 묶여야 한다.
    """
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_place_id = uuid4()
    trip_id = uuid4()
    candidate_id = uuid4()
    from_place_id = uuid4()
    to_place_id = uuid4()

    tp = SimpleNamespace(
        id=trip_place_id,
        trip_id=trip_id,
        place_id=from_place_id,
        initial_place_id=None,
        is_fixed=False,
    )
    trip = SimpleNamespace(id=trip_id, user_id=user.id)
    cand = SimpleNamespace(id=candidate_id, candidate_place_id=to_place_id, congestion_level="low")
    ranking = SimpleNamespace(id=uuid4())
    reason = SimpleNamespace(is_eligible=True, recommend_reason="추천", not_recommend_reason=None)
    route = SimpleNamespace(extra_minutes=5)

    svc.repo.get_trip_place_for_update = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_candidate_for_trip_place = MagicMock(return_value=cand)
    svc.repo.get_ranking_by_candidate = MagicMock(return_value=ranking)
    svc.repo.get_reason_by_candidate = MagicMock(return_value=reason)
    svc.repo.get_route_by_candidate = MagicMock(return_value=route)
    svc.repo.latest_analysis = MagicMock(return_value=SimpleNamespace(level="high"))
    svc.repo.create_replacement = MagicMock()
    svc.repo.log_interaction = MagicMock()
    svc.analysis_repo.clear_analysis_for_trip_place = MagicMock()
    svc.analysis_repo.write_analysis = MagicMock()

    call_order: list[str] = []
    svc.analysis_repo.clear_analysis_for_trip_place.side_effect = lambda *a, **k: call_order.append("clear")
    svc.analysis_repo.write_analysis.side_effect = lambda *a, **k: call_order.append("write")
    db.commit.side_effect = lambda: call_order.append("commit")

    result = svc.apply_replacement(trip_place_id, candidate_id, user)

    assert tp.place_id == to_place_id
    svc.analysis_repo.clear_analysis_for_trip_place.assert_called_once_with(trip_place_id)
    svc.analysis_repo.write_analysis.assert_called_once()
    assert call_order == ["clear", "write", "commit"]
    assert result["resolutionStatus"] == "replaced"
    svc.repo.get_trip_place_for_update.assert_called_once_with(trip_place_id)
    svc.repo.get_candidate_for_trip_place.assert_called_once_with(candidate_id, trip_place_id)


def test_apply_replacement_rejects_candidate_from_another_trip_place():
    """candidate_id가 다른 trip_place(다른 사용자 포함)의 추천 요청에서 나온 것이면
    get_candidate_for_trip_place()가 None을 돌려주고, 그대로 404 처리돼야 한다 —
    id만으로 조회하면 이 검증 없이 통과했었다(코드 리뷰로 발견)."""
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_place_id = uuid4()
    trip_id = uuid4()
    candidate_id = uuid4()

    tp = SimpleNamespace(id=trip_place_id, trip_id=trip_id, place_id=uuid4(), is_fixed=False)
    trip = SimpleNamespace(id=trip_id, user_id=user.id)

    svc.repo.get_trip_place_for_update = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_candidate_for_trip_place = MagicMock(return_value=None)

    with pytest.raises(AppError) as exc:
        svc.apply_replacement(trip_place_id, candidate_id, user)

    assert exc.value.status_code == 404
    svc.repo.get_candidate_for_trip_place.assert_called_once_with(candidate_id, trip_place_id)


def test_revert_replacement_clears_analysis_and_reverts_place():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_place_id = uuid4()
    trip_id = uuid4()
    replacement_id = uuid4()
    from_place_id = uuid4()
    to_place_id = uuid4()

    replacement = SimpleNamespace(
        id=replacement_id,
        trip_place_id=trip_place_id,
        from_place_id=from_place_id,
        to_place_id=to_place_id,
        reverted_at=None,
        ranking_id=uuid4(),
    )
    tp = SimpleNamespace(
        id=trip_place_id, trip_id=trip_id, place_id=to_place_id, resolution_status="replaced",
    )
    trip = SimpleNamespace(id=trip_id, user_id=user.id)

    svc.repo.get_replacement = MagicMock(return_value=replacement)
    svc.repo.get_trip_place_for_update = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    # active_replacement: 취소 대상 확인 시엔 이 replacement 자신, flush 후 재조회 시엔
    # 남은 게 없다고(=완전히 pending으로) 답하게 한다.
    svc.repo.active_replacement = MagicMock(side_effect=[replacement, None])
    svc.repo.log_interaction = MagicMock()
    svc.analysis_repo.clear_analysis_for_trip_place = MagicMock()

    result = svc.revert_replacement(replacement_id, user)

    assert tp.place_id == from_place_id
    assert tp.resolution_status == "pending"
    assert replacement.reverted_at is not None
    svc.analysis_repo.clear_analysis_for_trip_place.assert_called_once_with(trip_place_id)
    db.flush.assert_called_once()  # active_replacement 재조회 전에 reverted_at이 반영돼야 함
    assert result["resolutionStatus"] == "pending"


def test_revert_replacement_keeps_replaced_status_when_older_replacement_remains():
    """A→B→C로 두 번 교체된 뒤 최신(B→C)만 되돌리면, 아직 안 되돌린 A→B가 남아있으므로
    resolution_status가 "pending"이 아니라 "replaced"로 유지돼야 한다."""
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_place_id = uuid4()
    trip_id = uuid4()
    replacement_id = uuid4()
    older_replacement = SimpleNamespace(id=uuid4(), reverted_at=None)

    replacement = SimpleNamespace(
        id=replacement_id,
        trip_place_id=trip_place_id,
        from_place_id=uuid4(),
        to_place_id=uuid4(),
        reverted_at=None,
        ranking_id=uuid4(),
    )
    tp = SimpleNamespace(id=trip_place_id, trip_id=trip_id, place_id=uuid4(), resolution_status="replaced")
    trip = SimpleNamespace(id=trip_id, user_id=user.id)

    svc.repo.get_replacement = MagicMock(return_value=replacement)
    svc.repo.get_trip_place_for_update = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.active_replacement = MagicMock(side_effect=[replacement, older_replacement])
    svc.repo.log_interaction = MagicMock()
    svc.analysis_repo.clear_analysis_for_trip_place = MagicMock()

    result = svc.revert_replacement(replacement_id, user)

    assert tp.resolution_status == "replaced"
    assert result["resolutionStatus"] == "replaced"


def test_revert_replacement_rejects_when_not_the_latest_active_replacement():
    """A→B→C→B 패턴: place_id만 비교하면 오래된 A→B 교체도 "지금 place_id와 같다"는
    이유로 취소가 통과해버렸다. 실제로 지금 활성 상태인 교체(C→B, 다른 id)와 다르면
    거부해야 한다."""
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_place_id = uuid4()
    trip_id = uuid4()
    old_replacement_id = uuid4()
    currently_active = SimpleNamespace(id=uuid4(), reverted_at=None)

    old_replacement = SimpleNamespace(
        id=old_replacement_id,
        trip_place_id=trip_place_id,
        from_place_id=uuid4(),
        to_place_id=uuid4(),
        reverted_at=None,
        ranking_id=uuid4(),
    )
    tp = SimpleNamespace(id=trip_place_id, trip_id=trip_id, place_id=uuid4(), resolution_status="replaced")
    trip = SimpleNamespace(id=trip_id, user_id=user.id)

    svc.repo.get_replacement = MagicMock(return_value=old_replacement)
    svc.repo.get_trip_place_for_update = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.active_replacement = MagicMock(return_value=currently_active)

    with pytest.raises(AppError) as exc:
        svc.revert_replacement(old_replacement_id, user)

    assert exc.value.status_code == 409


def test_revert_replacement_rejects_when_already_reverted():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_place_id = uuid4()
    trip_id = uuid4()
    replacement_id = uuid4()

    replacement = SimpleNamespace(
        id=replacement_id, trip_place_id=trip_place_id, reverted_at=MagicMock(),
    )
    tp = SimpleNamespace(id=trip_place_id, trip_id=trip_id, place_id=uuid4())
    trip = SimpleNamespace(id=trip_id, user_id=user.id)

    svc.repo.get_replacement = MagicMock(return_value=replacement)
    svc.repo.get_trip_place_for_update = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)

    with pytest.raises(AppError) as exc:
        svc.revert_replacement(replacement_id, user)

    assert exc.value.status_code == 409


def test_build_guide_includes_saved_itinerary_fields():
    db = MagicMock()
    svc = RecommendationService(db)
    from_place_id = uuid4()
    to_place_id = uuid4()
    tp = SimpleNamespace(
        id=uuid4(),
        place_id=to_place_id,
        initial_place_id=from_place_id,
        position=1,
        visit_time=time(10, 0),
        stay_minutes=90,
    )
    trip = SimpleNamespace(
        id=uuid4(),
        title="서울 서촌 당일치기",
        travel_date=date(2026, 8, 15),
        status="confirmed",
        transport_mode="walk",
        region=SimpleNamespace(name="서울 종로구"),
        trip_places=[tp],
    )
    replacement = SimpleNamespace(
        from_place_id=from_place_id,
        reason_snapshot="혼잡 개선",
        extra_minutes=12,
        before_level="high",
        after_level="low",
    )

    svc.places.get_by_ids = MagicMock(
        return_value={
            from_place_id: SimpleNamespace(name="경복궁"),
            to_place_id: SimpleNamespace(name="서울한방진흥센터 일대"),
        }
    )
    svc.repo.active_replacements_map = MagicMock(return_value={tp.id: replacement})
    svc.repo.get_active_share_link = MagicMock(return_value=None)
    svc.repo.guide_entries = MagicMock(
        return_value=[
            SimpleNamespace(
                content=None,
                image_url="https://example.com/cover.png",
                display_order=0,
            )
        ]
    )

    result = svc.build_guide(trip)

    assert result["regionName"] == "서울 종로구"
    assert result["coverImageUrl"] == "https://example.com/cover.png"
    assert result["title"] == "서울 서촌 당일치기"
    assert result["visibility"] == "link"
    assert result["shareToken"] is None
    stop = result["stops"][0]
    assert stop["stayMinutes"] == 90
    assert stop["visitTime"] == "10:00"
    assert stop["extraMinutes"] == 12
    assert stop["beforeLevel"] == "high"
    assert stop["afterLevel"] == "low"
    assert stop["wasReplaced"] is True
    assert stop["replacedFrom"] == "경복궁"
    assert stop["placeName"] == "서울한방진흥센터 일대"


def test_build_guide_includes_public_visibility():
    db = MagicMock()
    svc = RecommendationService(db)
    trip = SimpleNamespace(
        id=uuid4(),
        title="공개 가이드",
        travel_date=None,
        status="confirmed",
        transport_mode="walk",
        region=None,
        trip_places=[],
    )
    svc.repo.guide_entries = MagicMock(return_value=[])
    svc.repo.get_active_share_link = MagicMock(
        return_value=SimpleNamespace(visibility="public", token="abc123XYZ")
    )

    result = svc.build_guide(trip)

    assert result["visibility"] == "public"
    assert result["shareToken"] == "abc123XYZ"


def test_create_share_link_creates_when_missing():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_id = uuid4()
    trip = SimpleNamespace(id=trip_id, user_id=user.id, status="confirmed")
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.lock_trip = MagicMock(return_value=trip)
    svc.repo.get_active_share_link = MagicMock(return_value=None)
    svc.repo.create_share_link = MagicMock()

    result = svc.create_share_link(trip_id, user, None)

    svc.repo.lock_trip.assert_called_once_with(trip_id)
    svc.repo.create_share_link.assert_called_once()
    created = svc.repo.create_share_link.call_args[0][0]
    assert created.visibility == "link"
    assert result["token"] == created.token
    db.commit.assert_called_once()


def test_create_share_link_upserts_visibility_and_keeps_token():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_id = uuid4()
    trip = SimpleNamespace(id=trip_id, user_id=user.id, status="confirmed")
    existing = SimpleNamespace(
        token="existing-token",
        visibility="link",
        expires_at=None,
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.lock_trip = MagicMock(return_value=trip)
    svc.repo.get_active_share_link = MagicMock(return_value=existing)
    svc.repo.create_share_link = MagicMock()

    result = svc.create_share_link(trip_id, user, "public")

    assert existing.visibility == "public"
    assert result["token"] == "existing-token"
    svc.repo.lock_trip.assert_called_once_with(trip_id)
    svc.repo.create_share_link.assert_not_called()
    db.commit.assert_called_once()


def test_create_share_link_without_visibility_keeps_public():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_id = uuid4()
    trip = SimpleNamespace(id=trip_id, user_id=user.id, status="confirmed")
    existing = SimpleNamespace(
        token="existing-token",
        visibility="public",
        expires_at=None,
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.lock_trip = MagicMock(return_value=trip)
    svc.repo.get_active_share_link = MagicMock(return_value=existing)
    svc.repo.create_share_link = MagicMock()

    result = svc.create_share_link(trip_id, user, None)

    assert existing.visibility == "public"
    assert result["token"] == "existing-token"
    svc.repo.create_share_link.assert_not_called()


def test_create_share_link_rejects_invalid_visibility():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_id = uuid4()
    svc.repo.get_trip_owned = MagicMock(
        return_value=SimpleNamespace(id=trip_id, user_id=user.id, status="confirmed")
    )
    svc.repo.lock_trip = MagicMock()

    with pytest.raises(AppError) as exc:
        svc.create_share_link(trip_id, user, "everyone")

    assert exc.value.status_code == 400
    svc.repo.lock_trip.assert_not_called()


def test_lock_trip_uses_for_update():
    from app.repositories.recommendation_repository import RecommendationRepository

    db = MagicMock()
    repo = RecommendationRepository(db)
    trip_id = uuid4()

    repo.lock_trip(trip_id)

    filtered = db.query.return_value.filter.return_value
    filtered.populate_existing.assert_called_once()
    filtered.populate_existing.return_value.with_for_update.assert_called_once()
    filtered.populate_existing.return_value.with_for_update.return_value.first.assert_called_once()
