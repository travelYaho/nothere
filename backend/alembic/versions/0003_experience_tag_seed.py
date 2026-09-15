"""(no-op) experience_tag 시드 — 0006/0007이 대신 처리함

Revision ID: 0003_exp_tag_seed
Revises: 0002_region_codes
Create Date: 2026-09-08
Edited: 2026-09-12 — 원래 여기서 experience_tag 9종을 새 id로 시드했는데, 다른 브랜치의
0006이 explicit id 1~10으로 이미 같은 태그를 먼저 시드해서 두 head가 갈라졌었다(그 문제를
0007이 병합). 이 리비전이 계속 독자적으로 INSERT를 하면 0007의 "대소문자 공존 검사"가
항상 걸려서 마이그레이션이 실패하므로, 이 리비전은 no-op으로 남긴다. 파일 자체(리비전 id)는
지우지 않는다 — 0007의 down_revision이 "0003_exp_tag_seed"를 참조하므로 삭제하면 마이그레이션
그래프가 깨진다.
"""

from typing import Sequence, Union

revision: str = "0003_exp_tag_seed"
down_revision: Union[str, Sequence[str], None] = "0002_region_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
