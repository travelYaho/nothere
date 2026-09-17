"""PlaceRepository.backfill_address_if_missing()의 실제 Postgres 동작 검증.

단위 테스트(tests/repositories/test_place_repository.py)는 db를 MagicMock으로 교체해서
"어떤 SQL을 보냈는지"만 확인한다 — 그 SQL이 실제 Postgres에서 문법적으로 유효한지,
정규식(``~ '^\\s*$'``)이 의도대로 매칭하는지, 진짜 동시 요청에서 한쪽만 반영되고 반환
객체가 최신 상태로 남는지는 mock으로 확인할 수 없다. 이 파일은 그 부분을 실제 DB로 채운다.

기본 ``pytest tests -q`` 실행에는 포함되지 않는다 — ``TEST_DATABASE_URL``이 설정된
경우에만 실행된다(그 값이 가리키는 Postgres는 마이그레이션이 이미 적용돼 있어야 한다).
로컬에서 돌리는 예:

    docker run -d --name yeogimalgo-verify-addr -e POSTGRES_PASSWORD=verify \\
      -e POSTGRES_DB=verify -p 55447:5432 postgis/postgis:16-3.4
    docker exec yeogimalgo-verify-addr psql -U postgres -d verify -c \\
      "CREATE SCHEMA IF NOT EXISTS auth; CREATE TABLE auth.users (id uuid PRIMARY KEY);"
    DATABASE_URL=postgresql://postgres:verify@localhost:55447/verify \\
      python -m alembic upgrade head
    TEST_DATABASE_URL=postgresql://postgres:verify@localhost:55447/verify \\
      python -m pytest tests/integration/test_place_address_backfill.py -v
"""
from __future__ import annotations

import os
import threading

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.repositories.place_repository import PlaceRepository

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="실제 Postgres가 필요한 통합 테스트 — TEST_DATABASE_URL이 설정된 경우에만 실행",
)

_PREFIX = "backfill-verify-"


@pytest.fixture
def sessionmaker_and_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM place WHERE tour_content_id LIKE :p"), {"p": f"{_PREFIX}%"})
    yield Session, engine
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM place WHERE tour_content_id LIKE :p"), {"p": f"{_PREFIX}%"})
    engine.dispose()


def test_regex_matches_whitespace_only_address_that_trim_would_miss(sessionmaker_and_engine):
    """TRIM()은 스페이스만 지우지만, 저장된 값이 탭/개행만 있어도 우리 정규식은 "비어
    있음"으로 잡아 보충해야 한다. RETURNING으로 받은 값도 실제 커밋된 DB 값과 일치해야
    한다."""
    Session, engine = sessionmaker_and_engine
    db = Session()
    repo = PlaceRepository(db)
    place = repo.get_or_create(
        source_type="tour_api", tour_content_id=f"{_PREFIX}1", name="테스트장소1",
        longitude=127.0, latitude=37.5,
    )
    db.commit()

    with engine.begin() as conn:
        conn.execute(text("UPDATE place SET address = '\t\n' WHERE id = :id"), {"id": place.id})

    status = repo.backfill_address_if_missing(place, "  서울 종로구 사직로 161  ")
    returned_address = place.address  # commit 전에 캡처 — expire_on_commit 영향 배제
    db.commit()

    assert status == "updated"
    assert returned_address == "서울 종로구 사직로 161"

    with Session() as check:
        row = check.execute(
            text("SELECT address FROM place WHERE id = :id"), {"id": place.id}
        ).first()
    assert row[0] == "서울 종로구 사직로 161"
    db.close()


def test_valid_existing_address_is_never_overwritten(sessionmaker_and_engine):
    Session, _engine = sessionmaker_and_engine
    db = Session()
    repo = PlaceRepository(db)
    place = repo.get_or_create(
        source_type="tour_api", tour_content_id=f"{_PREFIX}2", name="테스트장소2",
        longitude=127.0, latitude=37.5, address="원래 정상 주소",
    )
    db.commit()

    status = repo.backfill_address_if_missing(place, "다른 값으로 덮어쓰려는 시도")
    returned_address = place.address
    db.commit()

    assert status == "not_empty"
    assert returned_address == "원래 정상 주소"
    db.close()


def test_concurrent_backfill_loser_sees_winners_address_before_its_own_commit(
    sessionmaker_and_engine,
):
    """진짜 두 세션(스레드+독립 커넥션)이 동시에 같은 place의 빈 주소를 채우려 하면,
    하나만 실제로 반영되고(``"updated"``) 나머지는 ``"not_empty"``를 받는다.

    핵심 검증: 진 쪽의 반환 객체가 **자신의 db.commit() 이전**에 이미 이긴 세션이 커밋한
    값을 갖고 있어야 한다 — commit 이후에 값을 읽으면 SQLAlchemy의 기본
    ``expire_on_commit=True``가 알아서 최신값을 다시 읽어오므로, 그 시점에 값이 맞다는
    것만으로는 ``backfill_address_if_missing()`` 내부의 ``refresh()``가 실제로 한 일인지
    증명되지 않는다(2026-09-17, 코드 리뷰로 지적됨) — 그래서 반드시 commit 전에 값을
    캡처해서 비교한다.
    """
    Session, _engine = sessionmaker_and_engine
    setup_db = Session()
    setup_repo = PlaceRepository(setup_db)
    place = setup_repo.get_or_create(
        source_type="tour_api", tour_content_id=f"{_PREFIX}3", name="테스트장소3",
        longitude=127.0, latitude=37.5,
    )
    place_id = place.id
    setup_db.commit()
    setup_db.close()

    barrier = threading.Barrier(2)
    results: dict[str, tuple[str, str | None]] = {}

    def worker(name: str, address_value: str) -> None:
        db = Session()
        repo = PlaceRepository(db)
        place_local = repo.get_by_source("tour_api", f"{_PREFIX}3")
        barrier.wait()
        status = repo.backfill_address_if_missing(place_local, address_value)
        returned_address = place_local.address  # commit 전 캡처 — 이게 이번 라운드의 핵심 수정
        db.commit()
        results[name] = (status, returned_address)
        db.close()

    address_a, address_b = "세션A가 보낸 주소", "세션B가 보낸 주소"
    t1 = threading.Thread(target=worker, args=("A", address_a))
    t2 = threading.Thread(target=worker, args=("B", address_b))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    statuses = sorted(status for status, _ in results.values())
    assert statuses == ["not_empty", "updated"], results

    returned_addresses = {address for _, address in results.values()}
    assert returned_addresses == {address_a} or returned_addresses == {address_b}, results

    with Session() as check:
        row = check.execute(
            text("SELECT address FROM place WHERE id = :id"), {"id": place_id}
        ).first()
    assert row[0] in (address_a, address_b)
    assert {row[0]} == returned_addresses
