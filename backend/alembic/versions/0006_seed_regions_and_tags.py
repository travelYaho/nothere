"""seed regions and experience_tags

Revision ID: 0006_seed_regions_and_tags
Revises: 0005_guide_gallery
Create Date: 2026-09-09

STEP2 화면(지역/선호경험 선택)에 필요한 기초 데이터. 0001_unified 로 스키마를
통합하는 과정에서 이전 마이그레이션(0002_trip_domain_schema, 이미 삭제됨)에
있던 시드 INSERT 가 함께 옮겨지지 않아 실제 DB에는 빠져 있었다.

경험 태그 code/name 10종은 기획 확정 문서가 없어 잠정 값이다. 확정되면 이
시드만 교체하는 별도 마이그레이션을 추가하면 된다.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006_seed_regions_and_tags"
down_revision: Union[str, Sequence[str], None] = "0005_guide_gallery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO public.region (id, name, is_supported) VALUES
            (1, '서울특별시', true),
            (2, '부산광역시', true)
        ON CONFLICT (id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO public.experience_tag (id, code, name, is_active, display_order) VALUES
            (1, 'NATURE_WALK', '자연·산책', true, 1),
            (2, 'HISTORY_CULTURE', '역사·문화', true, 2),
            (3, 'ARCHITECTURE', '건축·랜드마크', true, 3),
            (4, 'PHOTO_VIEW', '사진·전망', true, 4),
            (5, 'FOOD_MARKET', '음식·시장', true, 5),
            (6, 'CAFE_REST', '카페·휴식', true, 6),
            (7, 'SHOPPING', '쇼핑', true, 7),
            (8, 'ACTIVITY', '액티비티·체험', true, 8),
            (9, 'EXHIBITION', '전시·공연', true, 9),
            (10, 'FAMILY', '가족·아이동반', true, 10)
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM public.experience_tag WHERE id BETWEEN 1 AND 10 "
        "AND code IN ('NATURE_WALK','HISTORY_CULTURE','ARCHITECTURE','PHOTO_VIEW',"
        "'FOOD_MARKET','CAFE_REST','SHOPPING','ACTIVITY','EXHIBITION','FAMILY');"
    )
    op.execute("DELETE FROM public.region WHERE id IN (1, 2);")
