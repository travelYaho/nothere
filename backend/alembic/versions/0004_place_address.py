"""add places.address

Revision ID: 0004_place_address
Revises: 0003_place_wait
Create Date: 2026-09-07

카카오 지오코딩("카카오맵" 제품 비활성화)이 당장 안 되는 상태라, "장소 직접
추가" 시 주소를 좌표로 바로 변환하지 않고 우선 텍스트로만 저장한다. 나중에
지오코딩이 가능해지면 이 컬럼 값으로 배치 변환해서 location 을 채운다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_place_address"
down_revision: Union[str, Sequence[str], None] = "0003_place_wait"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("places", sa.Column("address", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "address")
