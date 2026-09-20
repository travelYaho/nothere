"""요청별 소요 시간·DB 왕복·외부 API 시간을 로그 한 줄로 남긴다.

지연 원인을 추측이 아니라 수치로 좁히기 위한 측정용이다. 남기는 것은 라우트 경로(템플릿),
상태코드, 시간, DB 왕복 수, 외부 호출 이름별 횟수·시간뿐이고 SQL·파라미터·쿼리스트링·토큰은
남기지 않는다.
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger("app.perf")


@dataclass
class RequestStats:
    db_calls: int = 0
    db_seconds: float = 0.0
    external: dict[str, list[float]] = field(default_factory=dict)


_current: ContextVar[RequestStats | None] = ContextVar("request_stats", default=None)
_listeners_installed = False


@contextmanager
def timed_external(name: str):
    """외부 API 호출 하나를 `name`으로 집계한다. 요청 밖에서 불리면 아무것도 하지 않는다."""
    start = time.monotonic()
    try:
        yield
    finally:
        stats = _current.get()
        if stats is not None:
            stats.external.setdefault(name, []).append(time.monotonic() - start)


def install_db_listeners() -> None:
    global _listeners_installed
    if _listeners_installed:
        return
    _listeners_installed = True

    @event.listens_for(Engine, "before_cursor_execute")
    def _before(conn, cursor, statement, parameters, context, executemany):
        if context is not None and _current.get() is not None:
            context._perf_start = time.monotonic()

    @event.listens_for(Engine, "after_cursor_execute")
    def _after(conn, cursor, statement, parameters, context, executemany):
        stats = _current.get()
        started = getattr(context, "_perf_start", None)
        if stats is not None and started is not None:
            stats.db_calls += 1
            stats.db_seconds += time.monotonic() - started


def _format_external(external: dict[str, list[float]]) -> str:
    return ",".join(
        f"{name}:{len(durations)}x/{sum(durations):.2f}s" for name, durations in sorted(external.items())
    )


class PerfLogMiddleware:
    """`/api` 요청마다 총 소요 시간과 DB·외부 API 시간을 로그로 남기는 ASGI 미들웨어."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api"):
            await self.app(scope, receive, send)
            return

        stats = RequestStats()
        token = _current.set(stats)
        started = time.monotonic()
        status: int | None = None

        async def send_wrapper(message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            _current.reset(token)
            total = time.monotonic() - started
            external_seconds = sum(sum(durations) for durations in stats.external.values())
            route = getattr(scope.get("route"), "path", None) or scope["path"]
            # other = DB 커넥션 수립·핑, 앱 처리 등 위 항목에 잡히지 않는 시간.
            logger.info(
                "perf %s %s status=%s total=%.2fs db_calls=%d db=%.2fs ext=[%s] other=%.2fs",
                scope["method"],
                route,
                status,
                total,
                stats.db_calls,
                stats.db_seconds,
                _format_external(stats.external),
                total - stats.db_seconds - external_seconds,
            )
