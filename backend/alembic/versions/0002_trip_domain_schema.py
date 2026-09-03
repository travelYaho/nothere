"""trip domain schema (replaces schedules placeholder)

Revision ID: 0002_trip_domain
Revises: 0001_init
Create Date: 2026-09-04

1주차 플레이스홀더였던 schedules 를 폐기하고, 스키마 문서(파트1) 기준
Trip/TripPlace 및 연관 도메인 테이블(regions, experience_tags, places,
place_experience_tags, trip_preferred_experiences, trip_place_purposes,
user_long_term_preferences)을 생성한다. Region 2건/ExperienceTag 10종
시드 데이터도 함께 넣는다.
"""
from typing import Sequence, Union

import geoalchemy2  # noqa: F401  (Geography 컬럼 DDL 컴파일러 등록용 side-effect import)
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_trip_domain"
down_revision: Union[str, Sequence[str], None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 0. schedules(1주차 플레이스홀더) 제거 ---
    op.execute("DROP TRIGGER IF EXISTS schedules_set_updated_at ON schedules;")
    op.drop_index("ix_schedules_user_id", table_name="schedules")
    op.drop_table("schedules")

    # --- 1. PostGIS (Place.location) ---
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # --- 2. regions ---
    op.create_table(
        "regions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_supported", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- 3. experience_tags ---
    op.create_table(
        "experience_tags",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # --- 4. places ---
    op.create_table(
        "places",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False, server_default="tour_api"),
        sa.Column("tour_content_id", sa.String(length=50), nullable=True),
        sa.Column("region_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geography(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("is_recommendable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_places_region_id", "places", ["region_id"])
    op.create_index("ix_places_tour_content_id", "places", ["tour_content_id"])

    # --- 5. place_experience_tags ---
    op.create_table(
        "place_experience_tags",
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experience_tag_id", sa.SmallInteger(), nullable=False),
        sa.Column("weight", sa.Numeric(4, 3), nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="tour_category"),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["experience_tag_id"], ["experience_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("place_id", "experience_tag_id"),
    )

    # --- 6. trips ---
    op.create_table(
        "trips",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("region_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=True),
        sa.Column("companion_type", sa.String(length=50), nullable=True),
        sa.Column("transport_mode", sa.String(length=50), nullable=True),
        sa.Column("extra_time_limit_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("current_step", sa.SmallInteger(), nullable=False, server_default="2"),
        sa.Column("needs_reanalysis", sa.Boolean(), nullable=False, server_default=sa.false()),
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
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_id"], ["regions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trips_user_id", "trips", ["user_id"])
    op.create_index("ix_trips_region_id", "trips", ["region_id"])

    # --- 7. trip_preferred_experiences ---
    op.create_table(
        "trip_preferred_experiences",
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experience_tag_id", sa.SmallInteger(), nullable=False),
        sa.Column("weight", sa.Numeric(4, 3), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["experience_tag_id"], ["experience_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("trip_id", "experience_tag_id"),
    )

    # --- 8. trip_places ---
    op.create_table(
        "trip_places",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("initial_place_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("visit_time", sa.Time(), nullable=True),
        sa.Column("stay_minutes", sa.SmallInteger(), nullable=True, server_default="60"),
        sa.Column("is_fixed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resolution_status", sa.String(length=20), nullable=False, server_default="pending"),
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
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["initial_place_id"], ["places.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trip_places_trip_id", "trip_places", ["trip_id"])
    op.create_index("ix_trip_places_place_id", "trip_places", ["place_id"])

    # --- 9. trip_place_purposes ---
    op.create_table(
        "trip_place_purposes",
        sa.Column("trip_place_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose_tag_id", sa.SmallInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["trip_place_id"], ["trip_places.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purpose_tag_id"], ["experience_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("trip_place_id", "purpose_tag_id"),
    )

    # --- 10. user_long_term_preferences ---
    op.create_table(
        "user_long_term_preferences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experience_tag_id", sa.SmallInteger(), nullable=False),
        sa.Column("score", sa.Numeric(6, 3), nullable=False, server_default="0"),
        sa.Column("trip_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["experience_tag_id"], ["experience_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "experience_tag_id", name="uq_user_long_term_preference"),
    )
    op.create_index("ix_user_long_term_preferences_user_id", "user_long_term_preferences", ["user_id"])

    # --- 11. updated_at 트리거 연결 (set_updated_at() 는 0001 에서 이미 생성됨) ---
    for table in ("trips", "trip_places", "user_long_term_preferences"):
        op.execute(
            f"""
            CREATE TRIGGER {table}_set_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE PROCEDURE set_updated_at();
            """
        )

    # --- 12. 시드 데이터 ---
    op.execute(
        """
        INSERT INTO regions (id, name, is_supported) VALUES
            (1, '서울특별시', true),
            (2, '부산광역시', true);
        """
    )
    op.execute(
        """
        INSERT INTO experience_tags (id, code, name, is_active, display_order) VALUES
            (1, 'NATURE_WALK', '자연·산책', true, 1),
            (2, 'HISTORY_CULTURE', '역사·문화', true, 2),
            (3, 'ARCHITECTURE', '건축·랜드마크', true, 3),
            (4, 'PHOTO_VIEW', '사진·전망', true, 4),
            (5, 'FOOD_MARKET', '음식·시장', true, 5),
            (6, 'CAFE_REST', '카페·휴식', true, 6),
            (7, 'SHOPPING', '쇼핑', true, 7),
            (8, 'ACTIVITY', '액티비티·체험', true, 8),
            (9, 'EXHIBITION', '전시·공연', true, 9),
            (10, 'FAMILY', '가족·아이동반', true, 10);
        """
    )
    # 위 10종 code/name 은 확정 문서가 없어 잠정 값이다. 기획 확정 태그 목록이
    # 나오면 이 시드만 교체하면 되도록 별도 마이그레이션으로 분리해도 된다.


def downgrade() -> None:
    for table in ("user_long_term_preferences", "trip_places", "trips"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_set_updated_at ON {table};")

    op.drop_table("trip_place_purposes")
    op.drop_index("ix_trip_places_place_id", table_name="trip_places")
    op.drop_index("ix_trip_places_trip_id", table_name="trip_places")
    op.drop_table("trip_places")
    op.drop_table("trip_preferred_experiences")
    op.drop_index("ix_trips_region_id", table_name="trips")
    op.drop_index("ix_trips_user_id", table_name="trips")
    op.drop_table("trips")
    op.drop_table("place_experience_tags")
    op.drop_index("ix_places_tour_content_id", table_name="places")
    op.drop_index("ix_places_region_id", table_name="places")
    op.drop_table("places")
    op.drop_table("experience_tags")
    op.drop_index("ix_user_long_term_preferences_user_id", table_name="user_long_term_preferences")
    op.drop_table("user_long_term_preferences")
    op.drop_table("regions")

    # schedules 복원 (0001 정의 그대로)
    op.create_table(
        "schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=True),
        sa.Column("region_code", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
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
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedules_user_id", "schedules", ["user_id"])
    op.execute(
        """
        CREATE TRIGGER schedules_set_updated_at
        BEFORE UPDATE ON schedules
        FOR EACH ROW
        EXECUTE PROCEDURE set_updated_at();
        """
    )
