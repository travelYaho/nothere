"""route_cache upsert ON CONFLICT 회귀 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.clients.kakao_mobility import RouteResult
from app.domains.recommendation.route import RouteService


def test_put_cache_sql_uses_on_conflict_od_mode_provider():
    db = MagicMock()
    captured: list = []
    db.execute.side_effect = lambda stmt, **kwargs: captured.append(stmt)
    svc = RouteService(db, client=MagicMock())
    result = RouteResult(
        distance_m=1200,
        duration_seconds=480,
        provider="kakao_mobility",
        is_estimated=False,
        route_source="api",
    )

    svc._put_cache(uuid4(), uuid4(), "walk", result)

    assert captured, "_put_cache 가 execute 를 호출해야 함"
    sql = str(
        captured[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )
    assert "ON CONFLICT" in sql.upper()
    assert "origin_place_id" in sql
    assert "destination_place_id" in sql
    assert "transport_mode" in sql
    assert "provider" in sql
    db.flush.assert_called()
