"""merge heads: region/experience_tag 시드를 id 보존 방식으로 안전하게 정규화

Revision ID: 0007_merge_seed_heads
Revises: 0003_exp_tag_seed, 0006_seed_regions_and_tags
Create Date: 2026-09-09
Edited: 2026-09-12 — 원래는 대문자 코드(0006)를 DELETE하고 소문자 코드를 새로 INSERT하는
방식이었는데, id 1~10을 실제로 참조하는 데이터(trip_place_purpose 45건, trip_preferred_experience
65건, place_experience_tag 11건 — 직접 DB 조회로 확인)가 있어서 그대로 실행하면 FK 위반
또는(CASCADE라면) 121건 삭제로 이어진다. id는 그대로 두고 code/name/display_order만
UPDATE하는 방식으로 바꾼다. 대문자/소문자 코드가 이미 공존하는 비정상 상태를 먼저 검사해서,
있으면 조용히 넘어가지 않고 마이그레이션 자체를 실패시킨다(사람이 직접 병합해야 하는 상황).

이 리비전에서 region/experience_tag의 PK 시퀀스 보정도 같이 한다 — 0006이 explicit id로
INSERT하면서 시퀀스를 안 맞춰놔서(setval 없음), 지금 이 상태로 두 테이블 중 하나에 id
없이 새 행을 넣으면 기존 id와 충돌해 바로 실패한다(직접 조회로 확인: 두 시퀀스 다
last_value=id 1개 값에 머물러 있고 is_called=false).

전부 ``op.execute(SQL 문자열)``만 쓴다 — ``op.get_bind()``로 커넥션을 얻어 쿼리 결과를
Python으로 읽어 분기하면(``conn.execute(...).scalar()`` 등) alembic 오프라인 모드
(``alembic upgrade --sql``, tests/db/test_migration_offline.py가 검증)에서 실제 DB 없이
SQL만 렌더링할 수 없어 깨진다. 그래서 공존 검사·조건부 처리를 전부 PL/pgSQL DO 블록 안에서
(RAISE EXCEPTION 포함) 처리해 순수 SQL 텍스트로만 표현한다.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007_merge_seed_heads"
down_revision: Union[str, Sequence[str], None] = ("0003_exp_tag_seed", "0006_seed_regions_and_tags")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (레거시 대문자 code, 정식 snake_case code, 표시 이름, display_order)
# code: candidates.py의 CATEGORY_TAG_WEIGHTS/EXPERIENCE_TAG_KEYWORDS가 참조하는 값과 일치해야 함.
_TAG_RENAMES = [
    ("NATURE_WALK", "nature_walk", "자연·산책", 1),
    ("HISTORY_CULTURE", "history_culture", "역사·문화", 2),
    ("ARCHITECTURE", "architecture_space", "건축·랜드마크", 3),
    ("PHOTO_VIEW", "photo_view", "사진·전망", 4),
    ("FOOD_MARKET", "food_market", "음식·시장", 5),
    ("CAFE_REST", "cafe_rest", "카페·휴식", 6),
    ("SHOPPING", "shopping", "쇼핑", 7),
    ("ACTIVITY", "activity_experience", "액티비티·체험", 8),
    ("EXHIBITION", "exhibit_performance", "전시·공연", 9),
    ("FAMILY", "family_activity", "가족·아이동반", 10),
]

_REGIONS = ["서울특별시", "부산광역시"]


def _fix_sequence_sql(table: str) -> str:
    """<table>.id 시퀀스가 밀려 있으면(다음 nextval()이 기존 id와 충돌) 앞으로 당긴다.

    현재 값보다 "실제로 충돌하는" 경우에만 전진시키므로 재실행해도 안전하고, 이미 앞서 있는
    정상 시퀀스를 뒤로 돌리지 않는다. Postgres 시퀀스는 비트랜잭션이라 이 마이그레이션의
    나머지가 실패해서 롤백돼도 이 보정 자체는 되돌아가지 않는다 — 그래도 안전하므로 문제없다.
    """
    return f"""
    DO $$
    DECLARE seq text := pg_get_serial_sequence('{table}', 'id');
            max_id bigint; cur_val bigint; called boolean;
    BEGIN
      SELECT MAX(id) INTO max_id FROM {table};
      IF max_id IS NOT NULL THEN
        EXECUTE format('SELECT last_value, is_called FROM %s', seq) INTO cur_val, called;
        IF (called AND max_id > cur_val) OR (NOT called AND max_id >= cur_val) THEN
          PERFORM setval(seq, max_id, true);
        END IF;
      END IF;
    END $$;
    """


def _coexistence_check_sql() -> str:
    """대문자/소문자 코드가 이미 공존하는 태그가 있으면 마이그레이션 자체를 실패시킨다."""
    pairs = ", ".join(f"('{old}', '{new}')" for old, new, _, _ in _TAG_RENAMES)
    return f"""
    DO $$
    DECLARE conflict_count int;
    BEGIN
      SELECT count(*) INTO conflict_count
      FROM (VALUES {pairs}) AS pairs(old_code, new_code)
      WHERE EXISTS (SELECT 1 FROM experience_tag WHERE code = pairs.old_code)
        AND EXISTS (SELECT 1 FROM experience_tag WHERE code = pairs.new_code);
      IF conflict_count > 0 THEN
        RAISE EXCEPTION
          'experience_tag에 대문자/소문자 코드가 % 건 공존합니다 — 수동 병합이 필요합니다',
          conflict_count;
      END IF;
    END $$;
    """


def upgrade() -> None:
    # 1) 시퀀스 보정을 가장 먼저 — 아래 INSERT들이 시퀀스 충돌로 실패하지 않게 한다.
    op.execute(_fix_sequence_sql("region"))
    op.execute(_fix_sequence_sql("experience_tag"))

    # 2) 대문자/소문자 코드가 이미 공존하는 태그가 있는지 검사 — 있으면 즉시 중단한다.
    op.execute(_coexistence_check_sql())

    # 3) id는 유지하고 code/name/display_order만 정규화한다.
    #    old 코드 행이 있으면 UPDATE로 새 code로 바꾸고, old/new 둘 다 없으면(빈 DB 등)
    #    INSERT로 새로 만든다. UPDATE를 먼저 실행해서, old가 있었다면 그 시점부터 new가
    #    이미 존재하는 것으로 보이므로 뒤따르는 INSERT의 NOT EXISTS가 자연히 막아준다.
    for old_code, new_code, name, display_order in _TAG_RENAMES:
        op.execute(
            f"""
            UPDATE public.experience_tag
            SET code = '{new_code}', name = '{name}', display_order = {display_order}
            WHERE code = '{old_code}';
            """
        )
        op.execute(
            f"""
            INSERT INTO public.experience_tag (code, name, is_active, display_order)
            SELECT '{new_code}', '{name}', TRUE, {display_order}
            WHERE NOT EXISTS (SELECT 1 FROM public.experience_tag WHERE code = '{new_code}');
            """
        )

    # 4) region은 이름 기준으로 없을 때만 추가 — 기존과 동일, 안전.
    for name in _REGIONS:
        op.execute(
            f"""
            INSERT INTO public.region (name, is_supported)
            SELECT '{name}', TRUE
            WHERE NOT EXISTS (SELECT 1 FROM public.region WHERE name = '{name}');
            """
        )


def downgrade() -> None:
    # region은 일부러 안 건드린다 — "area_cd/signgu_cd가 NULL이면 이 마이그레이션이 만든 것"
    # 이라는 가정은 이제 성립하지 않는다(region.area_cd/signgu_cd를 더 이상 채우는 코드가
    # 없어 모든 region 행이 항상 NULL이다). 그 조건으로 삭제하면 0006이 만든 정상 행까지
    # 지울 수 있고, 이미 참조가 있으면 FK 에러로 downgrade 자체가 실패한다. 이 리비전이
    # 만든 게 확실한 건 태그 code뿐이라 그것만 되돌린다.
    for old_code, new_code, _, _ in _TAG_RENAMES:
        op.execute(
            f"UPDATE public.experience_tag SET code = '{old_code}' WHERE code = '{new_code}';"
        )
