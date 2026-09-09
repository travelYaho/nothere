"""Supabase 가 관리하는 auth.users 를 가리키는 읽기 전용 스텁 테이블이다.

Supabase Auth 는 이 테이블을 자체적으로 생성/관리하므로 Alembic 이 만들거나
건드리면 안 된다(`alembic/env.py` 의 `include_object` 가 schema="auth" 테이블을
autogenerate/DDL 대상에서 제외하는 이유). 다만 `Profile.id` 가 이 테이블을
참조하는 FK 를 선언하고 있어서, SQLAlchemy 가 관계를 구성(configure_mappers)할
때 대상 컬럼을 찾을 수 있도록 최소 컬럼만 가진 스텁을 metadata 에 등록해 둔다.
"""
from sqlalchemy import Table, Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base import Base

auth_users = Table(
    "users",
    Base.metadata,
    Column("id", PG_UUID(as_uuid=True), primary_key=True),
    schema="auth",
)
