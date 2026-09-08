"""unified schema Part0~3

Revision ID: 0001_unified
Revises:
Create Date: 2026-09-07

Source of Truth. backend/supabase/schema.sql 과 동일 내용.
schema.sql 로 이미 초기화했다면 upgrade 하지 말고 alembic stamp head 만 실행.
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "0001_unified"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA_SQL = Path(__file__).resolve().parents[2] / "supabase" / "schema.sql"

_DROP_ORDER = [
    "guide_entry",
    "share_link",
    "recommendation_interaction",
    "replacement",
    "route_cache",
    "recommendation_reason",
    "recommendation_route",
    "recommendation_ranking",
    "recommendation_candidate",
    "recommendation_request",
    "trip_place_analysis",
    "place_concentration_mapping",
    "concentration_spot",
    "user_long_term_preference",
    "place_experience_tag",
    "trip_preferred_experience",
    "trip_place_purpose",
    "trip_place",
    "trip",
    "place",
    "experience_tag",
    "region",
    "api_fetch_log",
    "profile",
    # legacy
    "schedule_places",
    "schedules",
    "profiles",
]


def upgrade() -> None:
    # 레거시 profiles/schedules/schedule_places DROP 은 하지 않는다.
    # 백필·검증 후 별도 정리 revision 에서만 삭제한다.
    sql = _SCHEMA_SQL.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    for table in _DROP_ORDER:
        op.execute(f"DROP TABLE IF EXISTS public.{table} CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS public.set_updated_at() CASCADE;")
