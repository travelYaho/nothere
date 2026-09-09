"""merge heads: region/experience_tag 시드 중복 정리

Revision ID: 0007_merge_seed_heads
Revises: 0003_exp_tag_seed, 0006_seed_regions_and_tags
Create Date: 2026-09-09

develop(0002/0003)과 이 브랜치(0004~0006)가 서로 독립적으로 region/experience_tag 시드를
추가하면서 head 가 두 개로 갈라졌다. 두 시드가 서로 다른 id/code 값을 explicit id 기준
ON CONFLICT DO NOTHING 으로 넣기 때문에, 두 마이그레이션이 실행되는 순서에 따라 먼저 id를
차지한 쪽이 이기고 나머지 쪽 행 전체가 조용히 스킵될 수 있다(예: 0002가 먼저 region id
1~3을 auto-increment로 차지하면 0006의 explicit id=1 서울특별시 INSERT가 통째로 무시됨).

특히 experience_tag.code 는 candidates.py 의 CATEGORY_TAG_WEIGHTS/EXPERIENCE_TAG_KEYWORDS가
참조하는 snake_case 값이 정본이라, 이 값이 비어 있으면 STEP6 후보 채점 로직이 조용히
아무 가중치도 못 찾는다. 그래서 id 대신 안정적인 자연키(태그 code / 지역명)를 기준으로
최종 시드 상태를 순서 무관하게 다시 맞춘다.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007_merge_seed_heads"
down_revision: Union[str, Sequence[str], None] = ("0003_exp_tag_seed", "0006_seed_regions_and_tags")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# code: candidates.py CATEGORY_TAG_WEIGHTS/EXPERIENCE_TAG_KEYWORDS 와 맞춘 snake_case 값.
# display_order: STEP2/STEP5 UI 노출 순서(0006 안).
_TAGS = [
    ("nature_walk", "자연·산책", 1),
    ("history_culture", "역사·문화", 2),
    ("architecture_space", "건축·랜드마크", 3),
    ("photo_view", "사진·전망", 4),
    ("food_market", "음식·시장", 5),
    ("cafe_rest", "카페·휴식", 6),
    ("shopping", "쇼핑", 7),
    ("activity_experience", "액티비티·체험", 8),
    ("exhibit_performance", "전시·공연", 9),
    ("family_activity", "가족·아이동반", 10),
]

# 0006이 explicit id로 넣었을 수 있는 대문자 코드 — 위 목록과 같은 태그의 중복 표기다.
_LEGACY_UPPER_CODES = [
    "NATURE_WALK", "HISTORY_CULTURE", "ARCHITECTURE", "PHOTO_VIEW", "FOOD_MARKET",
    "CAFE_REST", "SHOPPING", "ACTIVITY", "EXHIBITION", "FAMILY",
]

_REGIONS = ["서울특별시", "부산광역시"]


def upgrade() -> None:
    codes = ", ".join(f"'{c}'" for c in _LEGACY_UPPER_CODES)
    op.execute(f"DELETE FROM public.experience_tag WHERE code IN ({codes});")

    for code, name, display_order in _TAGS:
        op.execute(
            f"""
            INSERT INTO public.experience_tag (code, name, is_active, display_order)
            VALUES ('{code}', '{name}', TRUE, {display_order})
            ON CONFLICT (code) DO UPDATE SET display_order = EXCLUDED.display_order;
            """
        )

    for name in _REGIONS:
        op.execute(
            f"""
            INSERT INTO public.region (name, is_supported)
            SELECT '{name}', TRUE
            WHERE NOT EXISTS (SELECT 1 FROM public.region WHERE name = '{name}');
            """
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM public.region WHERE name IN ('서울특별시', '부산광역시') "
        "AND area_cd IS NULL AND signgu_cd IS NULL;"
    )
