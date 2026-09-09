"""experience_tag 시드 데이터 (STEP5 방문 목적 선택 / STEP6 후보 채점 공용)

Revision ID: 0003_exp_tag_seed
Revises: 0002_region_codes
Create Date: 2026-09-08

experience_tag 테이블 자체는 0001에서 만들어졌지만 실제 행이 하나도 없어서(어느 파트도
아직 채우지 않음) STEP5 목적 선택 UI와 STEP6 카테고리 기반 채점(candidates.py의
CATEGORY_TAG_WEIGHTS)이 참조할 code 값을 여기서 시드한다. code는 UNIQUE라 재실행해도 안전.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003_exp_tag_seed"
down_revision: Union[str, Sequence[str], None] = "0002_region_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TAGS = [
    ("nature_walk", "자연·산책"),
    ("history_culture", "역사·문화"),
    ("architecture_space", "건축·공간"),
    ("photo_view", "사진·전망"),
    ("food_market", "음식·시장"),
    ("cafe_rest", "카페·휴식"),
    ("activity_experience", "체험·활동"),
    ("exhibit_performance", "전시·공연"),
    ("family_activity", "가족 활동"),
]


def upgrade() -> None:
    for code, name in _TAGS:
        op.execute(
            f"""
            INSERT INTO public.experience_tag (code, name, is_active)
            VALUES ('{code}', '{name}', TRUE)
            ON CONFLICT (code) DO NOTHING;
            """
        )


def downgrade() -> None:
    codes = ", ".join(f"'{code}'" for code, _ in _TAGS)
    op.execute(f"DELETE FROM public.experience_tag WHERE code IN ({codes});")
