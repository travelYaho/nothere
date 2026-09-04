"""add places.expected_wait_minutes

Revision ID: 0003_place_wait
Revises: 0002_trip_domain
Create Date: 2026-09-04

"장소 직접 추가"(커스텀 장소)는 집중도 분석 대상이 아니라서
사용자가 직접 예상 대기시간을 입력한다. ERD 원본엔 없는 필드지만
이 기능에 실제로 필요해서 추가한다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_place_wait"
down_revision: Union[str, Sequence[str], None] = "0002_trip_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("places", sa.Column("expected_wait_minutes", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "expected_wait_minutes")
