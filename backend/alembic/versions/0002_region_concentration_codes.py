"""region 에 area_cd/signgu_cd 컬럼 추가 (더 이상 이 컬럼을 시드하지 않음)

Revision ID: 0002_region_codes
Revises: 0001_unified
Create Date: 2026-09-08
Edited: 2026-09-12 — 원래 여기서 종로구/중구/마포구를 region 행으로 시드했었는데, region은
시/도 단위(서울특별시/부산광역시, 0006/0007)로 이미 확정됐다. region에 구를 섞어 넣으면
지역 선택 목록에 시/도와 구가 같이 뜨는 문제가 생겨 시드를 제거한다. 컬럼 자체
(area_cd/signgu_cd)는 tests/db/test_models.py::test_region_matches_erd_exactly가 region의
허용 컬럼으로 이미 명시하고 있어 그대로 둔다 — 다만 region이 시/도 단위라 이 컬럼에 구
단위 코드를 의미 있게 담을 수 없으므로, 실제 분석 로직은 place.area_cd/signgu_cd(0008)를
쓰고 이 컬럼은 더 이상 읽지 않는다.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002_region_codes"
down_revision: Union[str, Sequence[str], None] = "0001_unified"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.region ADD COLUMN IF NOT EXISTS area_cd VARCHAR(20) NULL;")
    op.execute("ALTER TABLE public.region ADD COLUMN IF NOT EXISTS signgu_cd VARCHAR(20) NULL;")


def downgrade() -> None:
    op.execute("ALTER TABLE public.region DROP COLUMN IF EXISTS signgu_cd;")
    op.execute("ALTER TABLE public.region DROP COLUMN IF EXISTS area_cd;")
