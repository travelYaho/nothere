"""요청별 성능 측정 로그(app.core.perf)를 검증한다."""
import asyncio
import logging
import re

import pytest
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.perf import PerfLogMiddleware, install_db_listeners, timed_external

install_db_listeners()

_engine = create_engine("sqlite://")


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(PerfLogMiddleware)

    @app.get("/api/items/{item_id}")
    def item(item_id: str):
        with _engine.connect() as conn:
            conn.execute(text("select 1"))
            conn.execute(text("select 2"))
        with timed_external("kakao_directions"):
            pass
        with timed_external("kakao_directions"):
            pass
        with timed_external("tourapi_nearby"):
            pass
        return {"id": item_id}

    @app.get("/api/boom")
    def boom():
        raise RuntimeError("실패")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


@pytest.fixture
def client():
    return TestClient(_build_app(), raise_server_exceptions=False)


def _perf_lines(caplog):
    return [r.getMessage() for r in caplog.records if r.name == "app.perf"]


def test_logs_route_template_status_db_calls_and_external_counts(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.perf"):
        res = client.get("/api/items/abc-123?keyword=secret")

    assert res.status_code == 200
    (line,) = _perf_lines(caplog)
    assert line.startswith("perf GET /api/items/{item_id} status=200 ")
    assert "db_calls=2" in line
    assert re.search(r"total=\d+\.\d\ds", line)
    assert "kakao_directions:2x/" in line
    assert "tourapi_nearby:1x/" in line
    assert re.search(r"other=-?\d+\.\d\ds$", line)


def test_log_never_contains_path_values_or_query_string(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.perf"):
        client.get("/api/items/abc-123?keyword=secret")

    (line,) = _perf_lines(caplog)
    assert "abc-123" not in line
    assert "secret" not in line
    assert "select" not in line


def test_each_request_gets_its_own_counters(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.perf"):
        client.get("/api/items/a")
        client.get("/api/items/b")

    lines = _perf_lines(caplog)
    assert len(lines) == 2
    assert all("db_calls=2" in line and "kakao_directions:2x/" in line for line in lines)


def test_non_api_paths_are_not_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.perf"):
        client.get("/health")

    assert _perf_lines(caplog) == []


def test_still_logs_when_the_handler_raises(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.perf"):
        res = client.get("/api/boom")

    assert res.status_code == 500
    (line,) = _perf_lines(caplog)
    assert line.startswith("perf GET /api/boom status=unhandled_exception ")


def test_database_and_external_time_outside_a_request_is_ignored(caplog):
    with caplog.at_level(logging.INFO, logger="app.perf"):
        with _engine.connect() as conn:
            conn.execute(text("select 1"))
        with timed_external("kakao_directions"):
            pass

    assert _perf_lines(caplog) == []


_ID = "3f2b9c1e-1111-2222-3333-444455556666"


def test_unmatched_route_logs_a_fixed_label_instead_of_the_raw_path(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.perf"):
        res = client.get(f"/api/does-not-exist/{_ID}?keyword=secret")

    assert res.status_code == 404
    (line,) = _perf_lines(caplog)
    assert line.startswith("perf GET <unmatched> status=404 ")
    assert _ID not in line
    assert "secret" not in line


def test_cors_preflight_is_logged_without_the_request_path_values(caplog):
    app = FastAPI()
    app.add_middleware(CORSMiddleware, allow_origins=["http://front.test"], allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(PerfLogMiddleware)

    @app.post("/api/trips/{trip_id}/places")
    def add_place(trip_id: str):
        return {}

    with caplog.at_level(logging.INFO, logger="app.perf"):
        res = TestClient(app).options(
            f"/api/trips/{_ID}/places",
            headers={"Origin": "http://front.test", "Access-Control-Request-Method": "POST"},
        )

    assert res.status_code == 200
    (line,) = _perf_lines(caplog)
    assert line.startswith("perf OPTIONS <unmatched> status=200 ")
    assert _ID not in line


def test_response_less_exit_is_marked_instead_of_reported_as_a_status(caplog):
    async def silent_app(scope, receive, send):
        return

    async def run():
        await PerfLogMiddleware(silent_app)({"type": "http", "path": "/api/x", "method": "GET"}, None, None)

    with caplog.at_level(logging.INFO, logger="app.perf"):
        asyncio.run(run())

    (line,) = _perf_lines(caplog)
    assert "status=no_response" in line


def test_overlapping_requests_keep_separate_counters(caplog):
    app = FastAPI()
    app.add_middleware(PerfLogMiddleware)

    @app.get("/api/one")
    async def one():
        with timed_external("only_one"):
            await asyncio.sleep(0.05)
        return {}

    @app.get("/api/three")
    async def three():
        for _ in range(3):
            with timed_external("only_three"):
                await asyncio.sleep(0.02)
        return {}

    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await asyncio.gather(client.get("/api/one"), client.get("/api/three"))

    with caplog.at_level(logging.INFO, logger="app.perf"):
        asyncio.run(run())

    lines = {("/api/one" if "/api/one" in line else "/api/three"): line for line in _perf_lines(caplog)}
    assert "only_one:1x/" in lines["/api/one"] and "only_three" not in lines["/api/one"]
    assert "only_three:3x/" in lines["/api/three"] and "only_one" not in lines["/api/three"]
