"""recommendation upsert ON CONFLICT 회귀 테스트."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.db.models.recommendation import (
    RecommendationRanking,
    RecommendationReason,
    RecommendationRoute,
)
from app.repositories.recommendation_repository import RecommendationRepository


def _compile_upsert_sql(build_fn) -> str:
    """repository upsert 가 만드는 statement 를 가로채 컴파일한다."""
    db = MagicMock()
    captured: list = []

    def execute(stmt):
        captured.append(stmt)
        result = MagicMock()
        result.scalars.return_value.first.return_value = MagicMock()
        return result

    db.execute.side_effect = execute
    repo = RecommendationRepository(db)
    build_fn(repo)
    assert captured, "upsert 가 execute 를 호출해야 함"
    return str(
        captured[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )


def test_upsert_route_sql_uses_on_conflict_candidate_id():
    candidate_id = uuid4()
    route = RecommendationRoute(
        id=uuid4(),
        candidate_id=candidate_id,
        distance_prev_m=10,
        distance_next_m=20,
        extra_minutes=3,
        route_source="api",
        is_route_estimated=False,
        calculated_at=datetime.now(timezone.utc),
    )

    sql = _compile_upsert_sql(lambda repo: repo.upsert_route(route))
    assert "ON CONFLICT" in sql.upper()
    assert "candidate_id" in sql


def test_upsert_reason_sql_uses_on_conflict_candidate_id():
    reason = RecommendationReason(
        id=uuid4(),
        candidate_id=uuid4(),
        recommend_reason="추천",
        not_recommend_reason=None,
        reason_source_snapshot={"k": 1},
        is_eligible=True,
        exclusion_reason=None,
    )
    sql = _compile_upsert_sql(lambda repo: repo.upsert_reason(reason))
    assert "ON CONFLICT" in sql.upper()
    assert "candidate_id" in sql


def test_upsert_ranking_sql_uses_on_conflict_candidate_id():
    ranking = RecommendationRanking(
        id=uuid4(),
        candidate_id=uuid4(),
        route_score=Decimal("0.8"),
        congestion_score=None,
        operation_score=None,
        total_score=None,
        rank=None,
        scored_at=datetime.now(timezone.utc),
    )
    sql = _compile_upsert_sql(lambda repo: repo.upsert_ranking(ranking))
    assert "ON CONFLICT" in sql.upper()
    assert "candidate_id" in sql


def test_concurrent_upsert_route_same_candidate_does_not_raise():
    """동일 candidate_id 로 동시 upsert 해도 IntegrityError 없이 완료된다 (mock execute)."""
    candidate_id = uuid4()
    db = MagicMock()

    def execute(stmt):
        result = MagicMock()
        result.scalars.return_value.first.return_value = RecommendationRoute(
            id=uuid4(),
            candidate_id=candidate_id,
            distance_prev_m=1,
            distance_next_m=2,
            extra_minutes=0,
            route_source="api",
            is_route_estimated=False,
            calculated_at=datetime.now(timezone.utc),
        )
        return result

    db.execute.side_effect = execute
    repo = RecommendationRepository(db)

    def once(extra: int) -> RecommendationRoute:
        return repo.upsert_route(
            RecommendationRoute(
                id=uuid4(),
                candidate_id=candidate_id,
                distance_prev_m=extra,
                distance_next_m=extra,
                extra_minutes=extra,
                route_source="api",
                is_route_estimated=False,
                calculated_at=datetime.now(timezone.utc),
            )
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(once, range(4)))

    assert len(results) == 4
    assert db.execute.call_count == 4
    for call in db.execute.call_args_list:
        sql = str(
            call.args[0].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )
        assert "ON CONFLICT" in sql.upper()
