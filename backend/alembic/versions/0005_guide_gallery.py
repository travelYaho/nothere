"""add share_link, guide_entry, guide_like

Revision ID: 0005_guide_gallery
Revises: 0004_place_address
Create Date: 2026-09-07

가이드북 공개 갤러리·좋아요 기능에 필요한 테이블을 추가한다.
share_link/guide_entry 는 이 브랜치 스키마(trips 복수형)에는 아직 없어서
새로 만들고, guide_like 는 기획 문서(가이드북 공개 갤러리·좋아요 초안)의
설계를 그대로 따른다.
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
        "share_link",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="link"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "visibility in ('link', 'private', 'public')", name="ck_share_link_visibility"
        ),
    )
    op.create_index("ix_share_link_trip_id", "share_link", ["trip_id"])
    op.create_unique_constraint("uq_share_link_token", "share_link", ["token"])

    op.create_table(
        "guide_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trips.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "trip_place_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trip_places.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("entry_date", sa.Date(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("display_order", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_guide_entry_trip_id", "guide_entry", ["trip_id"])

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
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("share_link_id", "user_id", name="uq_guide_like_share_link_user"),
    )
    op.create_index("ix_guide_like_share_link_id", "guide_like", ["share_link_id"])
    op.create_index("ix_guide_like_user_id", "guide_like", ["user_id"])


def downgrade() -> None:
    op.drop_table("guide_like")
    op.drop_table("guide_entry")
    op.drop_table("share_link")
