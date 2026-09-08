"""RecommendationService 동작 검증 (DB/Kakao mock)."""
from __future__ import annotations

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


def test_confirm_raises_when_pending_congested():
    db = MagicMock()
    svc = RecommendationService(db)
    trip_id = uuid4()
    user = _user()
    trip = SimpleNamespace(id=trip_id, user_id=user.id, places=[])

    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.remaining_congested = MagicMock(
        return_value=[(SimpleNamespace(id=uuid4()), SimpleNamespace(level="high"))]
    )

    with pytest.raises(AppError) as exc:
        svc.confirm(trip_id, user)

    assert exc.value.status_code == 409
    assert exc.value.code == ErrorCode.UNRESOLVED_CONGESTED_PLACES
    assert exc.value.extra.get("pendingCount") == 1


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
    db.commit.assert_called()
