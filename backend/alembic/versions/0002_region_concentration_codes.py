"""region 에 집중률 API 지역 코드(area_cd/signgu_cd) 추가 + 표본 지역 시드

Revision ID: 0002_region_codes
Revises: 0001_unified
Create Date: 2026-09-08

Part2(집중도 분석) 이 region -> area_cd/signgu_cd 매핑 없이는 집중률 API를 호출할 지역을
알 수 없어 추가한다. schema.sql(0001)을 이미 적용한 환경도 있고 아직 적용 전인 환경도 있어
ADD COLUMN IF NOT EXISTS 로 양쪽 다 안전하게 처리한다. 시드는 실측 컷오프(analysis 서비스의
_LOW_CUTOFF/_MID_CUTOFF)를 측정한 서울 종로구/중구/마포구 3개 구만 우선 넣는다.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002_region_codes"
down_revision: Union[str, Sequence[str], None] = "0001_unified"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SEED_REGIONS = [
    ("서울 종로구", "11", "11110"),
    ("서울 중구", "11", "11140"),
    ("서울 마포구", "11", "11440"),
]


def upgrade() -> None:
    op.execute("ALTER TABLE public.region ADD COLUMN IF NOT EXISTS area_cd VARCHAR(20) NULL;")
    op.execute("ALTER TABLE public.region ADD COLUMN IF NOT EXISTS signgu_cd VARCHAR(20) NULL;")

    for name, area_cd, signgu_cd in _SEED_REGIONS:
        op.execute(
            f"""
            INSERT INTO public.region (name, is_supported, area_cd, signgu_cd)
            SELECT '{name}', TRUE, '{area_cd}', '{signgu_cd}'
            WHERE NOT EXISTS (
                SELECT 1 FROM public.region WHERE area_cd = '{area_cd}' AND signgu_cd = '{signgu_cd}'
            );
            """
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM public.region WHERE area_cd IS NOT NULL AND signgu_cd IS NOT NULL;"
    )
    op.execute("ALTER TABLE public.region DROP COLUMN IF EXISTS signgu_cd;")
    op.execute("ALTER TABLE public.region DROP COLUMN IF EXISTS area_cd;")
