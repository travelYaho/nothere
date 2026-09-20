"""직접 주소 장소 등록(PlaceService.add_custom_place_to_trip)의 좌표 저장을 실제 PostGIS로 검증한다.

단위 테스트는 repository를 mock으로 바꿔서 "create()에 좌표를 넘겼다"까지만 확인한다 — 그
좌표가 실제 place.location(GEOGRAPHY)에 위도·경도 순서 그대로 저장되고 get_place_coords()로
같은 값이 읽히는지, 지오코딩 실패나 저장 중 예외에서 place 행이 남지 않는지는 mock으로
확인할 수 없다. Kakao 호출(geocode_address)만 대체하고 나머지는 실제 DB를 쓴다.

기본 ``pytest tests -q`` 실행에는 포함되지 않는다 — ``TEST_DATABASE_URL``이 설정된 경우에만
실행된다(그 DB에는 마이그레이션이 이미 적용돼 있어야 한다). 로컬에서 돌리는 예:

    docker run -d --name yeogimalgo-verify-coords -e POSTGRES_PASSWORD=verify \\
      -e POSTGRES_DB=verify -p 55448:5432 postgis/postgis:16-3.4
    docker exec yeogimalgo-verify-coords psql -U postgres -d verify -c \\
      "CREATE SCHEMA IF NOT EXISTS auth; CREATE TABLE auth.users (id uuid PRIMARY KEY);"
    DATABASE_URL=postgresql://postgres:verify@localhost:55448/verify python -m alembic upgrade head
    TEST_DATABASE_URL=postgresql://postgres:verify@localhost:55448/verify \\
      python -m pytest tests/integration/test_custom_place_coordinates.py -v
"""
from __future__ import annotations

import os
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.clients.kakao_api import GeocodedAddress
from app.core.exceptions import AppError, ErrorCode
from app.db.models.trip import Trip
from app.schemas.place import CustomPlaceAddRequest
from app.schemas.user import CurrentUser
from app.services.place_service import PlaceService
from app.utils.geo import get_place_coords

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="실제 PostGIS가 필요한 통합 테스트 — TEST_DATABASE_URL이 설정된 경우에만 실행",
)

_NAME_PREFIX = "coords-verify-"


@pytest.fixture
def env():
    engine = create_engine(TEST_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    user_id = uuid4()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": user_id})
        conn.execute(
            text("INSERT INTO profile (id, nickname) VALUES (:id, 'verify')"), {"id": user_id}
        )
    setup = Session()
    trip = Trip(user_id=user_id, region_id=1, title=f"{_NAME_PREFIX}trip")
    setup.add(trip)
    setup.commit()
    trip_id = trip.id
    setup.close()

    yield Session, engine, CurrentUser(id=user_id, email="v@example.com", nickname="verify"), trip_id

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM trip WHERE id = :id"), {"id": trip_id})
        conn.execute(text("DELETE FROM place WHERE name LIKE :p"), {"p": f"{_NAME_PREFIX}%"})
        conn.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": user_id})
    engine.dispose()


def _payload(**overrides):
    defaults = dict(
        name=f"{_NAME_PREFIX}장소",
        address="서울 종로구 사직로 161 3층",
        base_address="서울 종로구 사직로 161",
    )
    defaults.update(overrides)
    return CustomPlaceAddRequest(**defaults)


def test_custom_place_is_stored_with_geocoded_coordinates_in_lat_lng_order(env):
    Session, engine, user, trip_id = env
    db = Session()
    try:
        with patch(
            "app.services.place_service.geocode_address",
            return_value=GeocodedAddress(latitude=37.5759, longitude=126.9768),
        ) as geocode:
            result = PlaceService(db).add_custom_place_to_trip(user, trip_id, _payload())

        geocode.assert_called_once_with("서울 종로구 사직로 161")
    finally:
        db.close()

    with Session() as check:
        row = check.execute(
            text(
                "SELECT source_type, address, is_recommendable, "
                "ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng "
                "FROM place WHERE id = :id"
            ),
            {"id": result.place_id},
        ).mappings().one()
        assert row["source_type"] == "custom"
        assert row["address"] == "서울 종로구 사직로 161 3층"
        assert row["is_recommendable"] is False
        assert row["lat"] == pytest.approx(37.5759)
        assert row["lng"] == pytest.approx(126.9768)

        # 경로 계산이 좌표 유무를 판단할 때 쓰는 함수가 (위도, 경도)를 그대로 돌려줘야 한다.
        coords = get_place_coords(check, result.place_id)
        assert coords == (pytest.approx(37.5759), pytest.approx(126.9768))

        linked = check.execute(
            text("SELECT count(*) FROM trip_place WHERE trip_id = :t AND place_id = :p"),
            {"t": trip_id, "p": result.place_id},
        ).scalar_one()
        assert linked == 1


def test_no_rows_are_written_when_the_address_cannot_be_located(env):
    Session, engine, user, trip_id = env
    db = Session()
    try:
        with patch("app.services.place_service.geocode_address", return_value=None):
            with pytest.raises(AppError) as exc_info:
                PlaceService(db).add_custom_place_to_trip(user, trip_id, _payload())
        assert exc_info.value.code == ErrorCode.ADDRESS_NOT_FOUND
    finally:
        db.close()

    with Session() as check:
        assert check.execute(
            text("SELECT count(*) FROM place WHERE name LIKE :p"), {"p": f"{_NAME_PREFIX}%"}
        ).scalar_one() == 0
        assert check.execute(
            text("SELECT count(*) FROM trip_place WHERE trip_id = :t"), {"t": trip_id}
        ).scalar_one() == 0


def test_place_row_is_not_left_behind_when_registering_fails_after_the_place_is_created(env):
    """place는 flush만 되고 commit은 trip_place 추가에서 한 번만 일어난다 — 그 사이에서 예외가
    나면(요청 종료 시 get_db가 세션을 닫는 것과 동일하게 close) place 행도 남지 않아야 한다."""
    Session, engine, user, trip_id = env
    db = Session()
    try:
        service = PlaceService(db)
        with patch(
            "app.services.place_service.geocode_address",
            return_value=GeocodedAddress(latitude=37.5759, longitude=126.9768),
        ), patch.object(service.trip_places, "add", side_effect=RuntimeError("저장 중 실패")):
            with pytest.raises(RuntimeError):
                service.add_custom_place_to_trip(user, trip_id, _payload())
    finally:
        db.close()

    with Session() as check:
        assert check.execute(
            text("SELECT count(*) FROM place WHERE name LIKE :p"), {"p": f"{_NAME_PREFIX}%"}
        ).scalar_one() == 0
