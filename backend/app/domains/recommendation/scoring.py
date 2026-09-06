"""경로(거리·추가시간) 점수 및 경로 기준 제외 판정."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class RouteScoreResult:
    route_score: float
    is_eligible: bool
    exclusion_reason: str | None
    snapshot: dict[str, Any]


def route_score_from_extra(extra_minutes: int, limit_minutes: int | None) -> float:
    """추가 이동시간이 적을수록 높은 점수. limit 대비 비율."""
    if limit_minutes is None or limit_minutes <= 0:
        limit = 30
    else:
        limit = limit_minutes
    if extra_minutes <= 0:
        return 1.0
    ratio = extra_minutes / float(limit)
    if ratio >= 1.0:
        return max(0.0, 1.0 - min(ratio, 2.0) * 0.5)
    return max(0.0, 1.0 - ratio * 0.5)


def compute_route_score(
    *,
    extra_minutes: int | None,
    limit_minutes: int | None,
    feasibility_status: str,
    route_available: bool,
) -> RouteScoreResult:
    """거리/경로 점수만 계산. 최종 합산(total)과 순위는 하지 않는다."""
    if not route_available or extra_minutes is None:
        return RouteScoreResult(
            route_score=0.0,
            is_eligible=False,
            exclusion_reason="route_unavailable",
            snapshot={"route_available": False},
        )

    if feasibility_status == "CLOSED":
        return RouteScoreResult(
            route_score=0.0,
            is_eligible=False,
            exclusion_reason="closed",
            snapshot={"feasibilityStatus": feasibility_status},
        )

    r_score = route_score_from_extra(extra_minutes, limit_minutes)
    exclusion: str | None = None
    eligible = True
    if limit_minutes is not None and extra_minutes > limit_minutes:
        eligible = False
        exclusion = "extra_time_exceeded"

    snapshot = {
        "routeScore": r_score,
        "extraMinutes": extra_minutes,
        "limitMinutes": limit_minutes,
        "feasibilityStatus": feasibility_status,
    }
    return RouteScoreResult(
        route_score=round(r_score, 4),
        is_eligible=eligible,
        exclusion_reason=exclusion,
        snapshot=snapshot,
    )


def build_reason_text(
    *,
    original_name: str,
    candidate_name: str,
    extra_minutes: int | None,
    congestion_level: str,
    experience_score: float,
) -> str:
    extra = f"약 {extra_minutes}분" if extra_minutes is not None else "소폭"
    level_kr = {"low": "낮아", "mid": "보통이며", "medium": "보통이며", "unknown": "불명확하지만"}.get(
        congestion_level, "개선되며"
    )
    return (
        f"{original_name}과 유사한 경험을 제공하는 {candidate_name}을(를) 추천합니다. "
        f"현재 일정 대비 추가 이동시간은 {extra}이고, 예상 집중도도 {level_kr} "
        f"대체 장소로 적합합니다. (경험 적합도 {experience_score:.0%})"
    )


def to_decimal(value: float) -> Decimal:
    return Decimal(str(round(value, 4)))
