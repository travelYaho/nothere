"""SQLAlchemy 엔진과 요청 단위 DB 세션을 관리한다.

이 프로젝트는 Supabase Auth 는 API 로 사용하고,
서비스 데이터는 DATABASE_URL 로 Supabase Postgres 에 직접 연결해 읽고 쓴다.
"""
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db import models as _models  # noqa: F401

# 기본 연결 옵션과 SQLAlchemy 엔진 옵션을 분리해 Supabase 연결 특성에 맞게 조정한다.
connect_args: dict = {"connect_timeout": 5}
engine_kwargs: dict = {"pool_pre_ping": True}

database_url = settings.sqlalchemy_database_url
if "supabase.co" in database_url or "supabase.com" in database_url:
    connect_args["sslmode"] = "require"

# Supabase transaction pooler (port 6543) does not support prepared statements / pooling well.
if ":6543/" in database_url or ":6543?" in database_url:
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 요청마다 새 Session 을 열고 응답 후 반드시 닫는다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> None:
    """앱 시작 시 DATABASE_URL 이 실제로 연결 가능한지 확인한다."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
