"""place에 구 단위 지역코드(area_cd/signgu_cd) + 외부 장소 중복 방지 제약 추가

Revision ID: 0008_place_district_codes
Revises: 0007_merge_seed_heads
Create Date: 2026-09-12

집중률 API는 구 단위(area_cd+signgu_cd) 조회가 필요한데 region은 시/도 단위로 확정됐다.
TourAPI 응답(lDongRegnCd/lDongSignguCd)이 장소 하나하나에 이미 구 코드를 담아 오므로,
region이 아니라 place에 이 코드를 직접 저장한다(app/domains/analysis/service.py가 이제
trip.region_id 대신 place.area_cd/signgu_cd로 동작).

(source_type, tour_content_id)에 일반 복합 UNIQUE도 같이 추가한다 — 동시 요청이 같은
외부 관광지를 중복 생성하지 못하게 막는다. Postgres는 UNIQUE 제약에서 NULL끼리 서로
다르다고 취급하므로 tour_content_id가 NULL인 custom 장소는 이 제약의 영향을 받지 않는다
(부분 인덱스가 필요 없다).

Edited: 2026-09-12 — 0001_unified가 실행 시점의 supabase/schema.sql을 그대로 읽어서 실행하는데
(0001 docstring: "schema.sql 과 동일 내용"), 이 세션에서 schema.sql의 place 테이블에 이미
area_cd/signgu_cd 컬럼과 (source_type, tour_content_id) UNIQUE를 반영해뒀다 — 즉 신규(빈) DB에서
`alembic upgrade head`를 돌리면 0001이 schema.sql을 실행하며 이 컬럼/제약을 이미 만들어버린
뒤에 0008이 다시 만들려다 DuplicateColumn으로 실패한다(실제 격리 컨테이너로 재현·확인함).
0002가 region.area_cd/signgu_cd에 이미 쓰고 있는 것과 같은 방어 패턴(ADD COLUMN IF NOT EXISTS)
으로 맞춘다 — 이미 head인 실제 공유 Supabase(0008 미적용)에서는 컬럼이 없으므로 정상적으로
새로 추가되고, 신규 DB에서는 0001이 이미 만든 걸 건너뛴다. UNIQUE 제약은 IF NOT EXISTS 구문이
없어(구버전 Postgres 호환) 컬럼 조합 기준으로 존재 여부를 직접 확인하는 DO 블록으로 감싼다.

Edited: 2026-09-14 — 코드 리뷰로 두 가지 보완.
1. 제약 존재 확인 쿼리가 스키마 제한 없이 relname='place'만 봐서, 다른 스키마에 우연히
   같은 이름의 테이블·제약이 있으면 오판할 수 있었다 — public 스키마로 명시 제한.
2. 이 마이그레이션 이전 배포 코드는 SELECT-then-INSERT라 동시 요청 두 개가 같은
   (source_type, tour_content_id)로 place를 동시에 만들면 이론적으로 중복 행이 생길 수
   있었다(3차 조사에서 이 DB엔 실제로 0건임을 직접 확인했지만, 그 확인에 영원히 기대는
   대신 방어적으로 짜는 게 맞다). 중복이 있으면 ALTER TABLE이 알아보기 힘든 Postgres 기본
   에러로 실패하는 대신, 0007의 태그 공존 검사와 같은 방식으로 먼저 검사해서 명확한 이유와
   함께 그 자리에서 실패시킨다 — 자동 병합(대표 행 선정 + 여러 테이블 FK 재연결)은 하지
   않는다(중복이 실제로 발견되면 그때 상황에 맞게 수동으로 처리하는 게 더 안전하다).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0008_place_district_codes"
down_revision: Union[str, Sequence[str], None] = "0007_merge_seed_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHECK_NO_DUPLICATE_PLACES_SQL = """
DO $$
DECLARE dup_count int;
BEGIN
  SELECT count(*) INTO dup_count FROM (
    SELECT source_type, tour_content_id
    FROM public.place
    WHERE source_type IS NOT NULL AND tour_content_id IS NOT NULL
    GROUP BY source_type, tour_content_id
    HAVING count(*) > 1
  ) dups;
  IF dup_count > 0 THEN
    RAISE EXCEPTION
      'place에 (source_type, tour_content_id) 중복이 % 건 있어 UNIQUE 제약을 추가할 수 없습니다 — 수동 병합이 필요합니다',
      dup_count;
  END IF;
END $$;
"""

_ADD_UNIQUE_CONSTRAINT_SQL = """
DO $$
DECLARE has_unique boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    WHERE t.relname = 'place'
      AND t.relnamespace = 'public'::regnamespace
      AND c.contype = 'u'
      AND c.conkey = ARRAY[
        (SELECT attnum FROM pg_attribute WHERE attrelid = t.oid AND attname = 'source_type'),
        (SELECT attnum FROM pg_attribute WHERE attrelid = t.oid AND attname = 'tour_content_id')
      ]
  ) INTO has_unique;
  IF NOT has_unique THEN
    ALTER TABLE public.place
      ADD CONSTRAINT uq_place_source_type_tour_content_id UNIQUE (source_type, tour_content_id);
  END IF;
END $$;
"""


def upgrade() -> None:
    op.execute("ALTER TABLE public.place ADD COLUMN IF NOT EXISTS area_cd VARCHAR(20) NULL;")
    op.execute("ALTER TABLE public.place ADD COLUMN IF NOT EXISTS signgu_cd VARCHAR(20) NULL;")
    op.execute(_CHECK_NO_DUPLICATE_PLACES_SQL)
    op.execute(_ADD_UNIQUE_CONSTRAINT_SQL)


def downgrade() -> None:
    op.execute("ALTER TABLE public.place DROP CONSTRAINT IF EXISTS uq_place_source_type_tour_content_id;")
    op.execute("ALTER TABLE public.place DROP COLUMN IF EXISTS signgu_cd;")
    op.execute("ALTER TABLE public.place DROP COLUMN IF EXISTS area_cd;")
