"""경로 점수 단위 테스트."""
from app.domains.recommendation.scoring import compute_route_score, route_score_from_extra


def test_extra_time_exceeded():
    result = compute_route_score(
        extra_minutes=20,
        limit_minutes=15,
        feasibility_status="OPEN_CONFIRMED",
        route_available=True,
    )
    assert result.is_eligible is False
    assert result.exclusion_reason == "extra_time_exceeded"
    assert result.route_score > 0


def test_route_unavailable():
    result = compute_route_score(
        extra_minutes=None,
        limit_minutes=15,
        feasibility_status="OPEN_CONFIRMED",
        route_available=False,
    )
    assert result.exclusion_reason == "route_unavailable"
    assert result.route_score == 0.0


def test_happy_path_route_score():
    result = compute_route_score(
        extra_minutes=5,
        limit_minutes=15,
        feasibility_status="OPEN_CONFIRMED",
        route_available=True,
    )
    assert result.is_eligible is True
    assert result.route_score > 0.7


def test_route_score_zero_extra():
    assert route_score_from_extra(0, 15) == 1.0
