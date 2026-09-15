"""Trip 도메인 모델이 스키마 문서(파트1) 및 마이그레이션과 일치하는지 검증한다.

실제 Supabase 연결 없이도 돌아가야 하는 테스트다. 기존 코드가 이미
`sqlalchemy.dialects.postgresql.UUID`/`geoalchemy2.Geography` 처럼 Postgres
전용 타입을 쓰기 때문에 `Base.metadata.create_all()` 을 SQLite 에 대고 돌리면
DDL 컴파일 자체가 실패한다. 그래서 여기서는 DB 에 아무것도 만들지 않고
`Base.metadata` 를 정적으로 검사해서 컬럼/PK/FK/관계 구성만 확인한다.
"""
from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app.db.models import (  # noqa: F401  (import 자체가 관계 등록을 트리거)
    ExperienceTag,
    GuideEntry,
    GuideLike,
    Place,
    PlaceExperienceTag,
    Profile,
    Region,
    ShareLink,
    Trip,
    TripPlace,
    TripPlacePurpose,
    TripPreferredExperience,
    UserLongTermPreference,
)


def _columns(table_name: str) -> set[str]:
    return set(Base.metadata.tables[table_name].columns.keys())


def test_all_mappers_configure_without_error():
    """관계(FK 조인 포함) 전체가 문제없이 구성되는지 확인한다.

    profiles.id -> auth.users.id FK 처럼 스키마 밖 테이블을 참조하는 관계가
    하나라도 깨지면 앱의 첫 ORM 쿼리에서 바로 터지므로 가장 먼저 검증한다.
    """
    configure_mappers()


def test_schedules_table_is_gone():
    """1주차 플레이스홀더 schedules 테이블이 metadata 에서 완전히 빠졌는지 확인한다."""
    assert "schedules" not in Base.metadata.tables


def test_region_matches_erd_exactly():
    """Region 은 스키마 문서(id/name/is_supported) + 집중률 API 연동용 지역 코드
    (area_cd/signgu_cd) 외 컬럼을 추가하지 않는다.
    """
    assert _columns("region") == {"id", "name", "is_supported", "area_cd", "signgu_cd"}


def test_place_uses_geography_location_not_lat_lng():
    """Place.location 은 위경도 분리 컬럼이 아니라 GEOGRAPHY 단일 컬럼이어야 한다.

    expected_wait_minutes/address 는 ERD 원본엔 없지만, "장소 직접 추가"(커스텀
    장소) 기능에 실제로 필요해 의도적으로 추가한 컬럼이라 허용 목록에 포함한다.
    address 는 Kakao 지오코딩이 비활성화된 동안 좌표 대신 임시로 저장하는
    주소 원문이다. area_cd/signgu_cd는 집중률 API(TatsCnctrRateService)가 요구하는
    구 단위 코드 — region이 시/도 단위라 이 값을 못 담아서 place에 직접 둔다
    (TourAPI 응답의 lDongRegnCd/lDongSignguCd 기준).
    """
    columns = _columns("place")
    assert columns == {
        "id",
        "source_type",
        "tour_content_id",
        "region_id",
        "name",
        "location",
        "is_recommendable",
        "expected_wait_minutes",
        "address",
        "area_cd",
        "signgu_cd",
    }
    assert "latitude" not in columns
    assert "longitude" not in columns


def test_trip_place_purpose_composite_key_matches_erd():
    table = Base.metadata.tables["trip_place_purpose"]
    assert {c.name for c in table.primary_key.columns} == {"trip_place_id", "purpose_tag_id"}
    assert _columns("trip_place_purpose") == {"trip_place_id", "purpose_tag_id", "created_at"}


def test_trip_preferred_experience_composite_key_matches_erd():
    table = Base.metadata.tables["trip_preferred_experience"]
    assert {c.name for c in table.primary_key.columns} == {"trip_id", "experience_tag_id"}
    assert _columns("trip_preferred_experience") == {"trip_id", "experience_tag_id", "weight"}


def test_trip_place_has_expected_columns():
    columns = _columns("trip_place")
    expected = {
        "id",
        "trip_id",
        "place_id",
        "initial_place_id",
        "position",
        "visit_time",
        "stay_minutes",
        "is_fixed",
        "resolution_status",
        "created_at",
        "updated_at",
    }
    assert columns == expected


def test_trip_place_defaults_are_pending_and_not_fixed():
    """TripPlace 컬럼 기본값(INSERT 시 적용)이 API 명세와 일치하는지 확인한다.

    SQLAlchemy 의 `default=` 는 flush 시점에 적용되는 컬럼 기본값이라
    아직 세션에 넣지 않은 객체를 만들어서는 확인할 수 없다. 그래서
    Column.default.arg 를 직접 검사한다.
    """
    table = Base.metadata.tables["trip_place"]
    assert table.columns["is_fixed"].default.arg is False
    assert table.columns["resolution_status"].default.arg == "pending"


def test_profile_has_no_schedules_relationship():
    """1주차 플레이스홀더였던 schedules 관계가 Profile 에 남아있지 않은지 확인한다."""
    assert not hasattr(Profile, "schedules")


def test_share_link_has_expected_columns_and_visibility_check():
    columns = _columns("share_link")
    assert columns == {
        "id",
        "trip_id",
        "token",
        "visibility",
        "created_at",
        "expires_at",
        "revoked_at",
    }
    table = Base.metadata.tables["share_link"]
    assert table.columns["visibility"].default.arg == "link"
    check_names = {c.name for c in table.constraints if hasattr(c, "sqltext")}
    assert "ck_share_link_visibility" in check_names


def test_guide_entry_has_expected_columns():
    assert _columns("guide_entry") == {
        "id",
        "trip_id",
        "trip_place_id",
        "entry_date",
        "image_url",
        "image_key",
        "image_original_name",
        "image_content_type",
        "content",
        "is_public",
        "display_order",
        "created_at",
        "updated_at",
    }


def test_guide_like_has_unique_constraint_on_share_link_and_user():
    table = Base.metadata.tables["guide_like"]
    assert _columns("guide_like") == {"id", "share_link_id", "user_id", "created_at"}
    unique_cols = {
        tuple(sorted(c.name for c in constraint.columns))
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("share_link_id", "user_id") in unique_cols


def test_place_experience_tag_and_trip_preferred_experience_share_experience_tags():
    """PlaceExperienceTag/TripPreferredExperience 가 같은 experience_tags 를 참조하는지 확인한다."""
    place_tag_fk = next(iter(Base.metadata.tables["place_experience_tag"].columns["experience_tag_id"].foreign_keys))
    trip_pref_fk = next(iter(Base.metadata.tables["trip_preferred_experience"].columns["experience_tag_id"].foreign_keys))
    assert place_tag_fk.column.table.name == "experience_tag"
    assert trip_pref_fk.column.table.name == "experience_tag"
