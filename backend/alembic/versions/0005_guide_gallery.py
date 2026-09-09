"""add guide_like

Revision ID: 0005_guide_gallery
Revises: 0004_place_address
Create Date: 2026-09-09

가이드북 공개 갤러리·좋아요 기능에 필요한 테이블을 추가한다.
share_link/guide_entry 는 0001_unified 에 이미 있어서 guide_like 만 새로
만든다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_guide_gallery"
down_revision: Union[str, Sequence[str], None] = "0004_place_address"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guide_like",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "share_link_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("share_link.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profile.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("share_link_id", "user_id", name="uq_guide_like_share_link_user"),
    )
    op.create_index("ix_guide_like_share_link_id", "guide_like", ["share_link_id"])
    op.create_index("ix_guide_like_user_id", "guide_like", ["user_id"])


def downgrade() -> None:
    op.drop_table("guide_like")
