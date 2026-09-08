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

    def execute(stmt, **kwargs):
        captured.append((stmt, kwargs))
        result = MagicMock()
        result.scalars.return_value.first.return_value = MagicMock()
        return result

    db.execute.side_effect = execute
    repo = RecommendationRepository(db)
    build_fn(repo)
    assert captured, "upsert 가 execute 를 호출해야 함"
    stmt, kwargs = captured[0]
    assert kwargs.get("execution_options") == {"populate_existing": True}
    return str(
        stmt.compile(
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

    def execute(stmt, **kwargs):
        assert kwargs.get("execution_options") == {"populate_existing": True}
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


def test_upsert_route_refreshes_existing_identity_map_entity():
    """같은 Session에 이미 로드된 엔터티가 있으면 RETURNING 값으로 갱신되어 반환된다."""
    candidate_id = uuid4()
    existing = RecommendationRoute(
        id=uuid4(),
        candidate_id=candidate_id,
        distance_prev_m=10,
        distance_next_m=20,
        extra_minutes=1,
        route_source="old",
        is_route_estimated=True,
        calculated_at=datetime.now(timezone.utc),
    )
    now = datetime.now(timezone.utc)
    db = MagicMock()

    def execute(stmt, **kwargs):
        assert kwargs.get("execution_options") == {"populate_existing": True}
        # populate_existing 시뮬레이션: identity-map 엔터티 속성을 RETURNING 결과로 덮어씀
        existing.distance_prev_m = 100
        existing.distance_next_m = 200
        existing.extra_minutes = 5
        existing.route_source = "api"
        existing.is_route_estimated = False
        existing.calculated_at = now
        result = MagicMock()
        result.scalars.return_value.first.return_value = existing
        return result

    db.execute.side_effect = execute
    repo = RecommendationRepository(db)

    returned = repo.upsert_route(
        RecommendationRoute(
            id=uuid4(),
            candidate_id=candidate_id,
            distance_prev_m=100,
            distance_next_m=200,
            extra_minutes=5,
            route_source="api",
            is_route_estimated=False,
            calculated_at=now,
        )
    )

    assert returned is existing
    assert returned.distance_prev_m == 100
    assert returned.distance_next_m == 200
    assert returned.extra_minutes == 5
    assert returned.route_source == "api"
    assert returned.is_route_estimated is False
