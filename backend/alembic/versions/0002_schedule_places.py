"""add schedule_places

Revision ID: 0002_schedule_places
Revises: 0001_init
Create Date: 2026-08-30

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_schedule_places"
down_revision: Union[str, Sequence[str], None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedule_places",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stay_minutes", sa.Integer(), nullable=True),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_places_schedule_id", "schedule_places", ["schedule_id"])
    op.execute(
        """
        CREATE TRIGGER schedule_places_set_updated_at
        BEFORE UPDATE ON schedule_places
        FOR EACH ROW
        EXECUTE PROCEDURE set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS schedule_places_set_updated_at ON schedule_places;")
    op.drop_index("ix_schedule_places_schedule_id", table_name="schedule_places")
    op.drop_table("schedule_places")
