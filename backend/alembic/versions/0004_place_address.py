"""add place.address, place.expected_wait_minutes, experience_tag.display_order,
trip.updated_at, trip_place.created_at/updated_at

Revision ID: 0004_place_address
Revises: 0001_unified
Create Date: 2026-09-09

0001_unified 이후 이 브랜치(STEP2/STEP3, 방문목적)에서 실무적으로 필요해진
컬럼을 추가한다.

- place.address: 카카오 지오코딩("카카오맵" 제품 비활성화)이 당장 안 되는
  상태라, "장소 직접 추가" 시 주소를 좌표로 바로 변환하지 않고 우선 텍스트로만
  저장한다. 나중에 지오코딩이 가능해지면 이 컬럼 값으로 배치 변환해서
  location 을 채운다.
- place.expected_wait_minutes: 커스텀 장소(is_recommendable=False)는 집중도
  분석 대상이 아니라서 사용자가 직접 예상 대기시간을 입력한다.
- experience_tag.display_order: STEP2/방문목적 UI에 10종 태그를 일정한
  순서로 노출하기 위한 컬럼.
- trip.updated_at / trip_place.created_at,updated_at: 홈 화면의 "진행 중
  일정" 최신순 정렬, 장소 방문시간/체류시간 수정 응답에 필요하다.
- trip.current_step: STEP2 완료 = STEP3 진입이 항상 명시적으로 설정되므로
  NOT NULL DEFAULT 2 로 강화한다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_place_address"
down_revision: Union[str, Sequence[str], None] = "0001_unified"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("place", sa.Column("address", sa.String(length=300), nullable=True))
    op.add_column(
        "place", sa.Column("expected_wait_minutes", sa.SmallInteger(), nullable=True)
    )
    op.add_column(
        "experience_tag",
        sa.Column("display_order", sa.SmallInteger(), nullable=False, server_default="0"),
    )

    op.add_column(
        "trip",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute(
        """
        CREATE TRIGGER trip_set_updated_at
        BEFORE UPDATE ON public.trip
        FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();
        """
    )

    op.execute("UPDATE public.trip SET current_step = 2 WHERE current_step IS NULL")
    op.alter_column(
        "trip",
        "current_step",
        existing_type=sa.SmallInteger(),
        nullable=False,
        server_default="2",
    )

    op.add_column(
        "trip_place",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "trip_place",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute(
        """
        CREATE TRIGGER trip_place_set_updated_at
        BEFORE UPDATE ON public.trip_place
        FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trip_place_set_updated_at ON public.trip_place")
    op.drop_column("trip_place", "updated_at")
    op.drop_column("trip_place", "created_at")

    op.alter_column(
        "trip",
        "current_step",
        existing_type=sa.SmallInteger(),
        nullable=True,
        server_default=None,
    )
    op.execute("DROP TRIGGER IF EXISTS trip_set_updated_at ON public.trip")
    op.drop_column("trip", "updated_at")
    op.drop_column("experience_tag", "display_order")
    op.drop_column("place", "expected_wait_minutes")
    op.drop_column("place", "address")
