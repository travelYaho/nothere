"""PlaceRepository.get_or_create() 단위 테스트 — 정상 생성 / 충돌 폴백 경로.

동시 요청 두 세션 간 진짜 경쟁 상태 테스트는 실제 DB 커넥션이 필요해 여기 넣지 않는다
(통합 테스트로 별도 관리). 여기서는 각 경로가 올바른 저장소 메서드를 부르는지만 검증한다.
"""
from unittest.mock import MagicMock
from uuid import uuid4

from app.repositories.place_repository import PlaceRepository, _classify_district_code_backfill


def test_get_by_sources_returns_empty_dict_without_query_when_no_valid_pairs():
    db = MagicMock()
    repo = PlaceRepository(db)

    result = repo.get_by_sources([("tour_api", None), ("tour_api", "")])

    assert result == {}
    db.query.assert_not_called()


def test_get_by_sources_builds_dict_keyed_by_source_type_and_content_id():
    db = MagicMock()
    place1 = MagicMock(source_type="tour_api", tour_content_id="1")
    place2 = MagicMock(source_type="tour_api", tour_content_id="2")
    db.query.return_value.filter.return_value.all.return_value = [place1, place2]
    repo = PlaceRepository(db)

    result = repo.get_by_sources([("tour_api", "1"), ("tour_api", "2"), ("tour_api", "3")])

    assert result == {("tour_api", "1"): place1, ("tour_api", "2"): place2}
    assert ("tour_api", "3") not in result  # DB에 없는 건 그냥 빠짐(에러 아님)


def test_get_by_ids_returns_empty_dict_without_query_for_empty_list():
    db = MagicMock()
    repo = PlaceRepository(db)

    result = repo.get_by_ids([])

    assert result == {}
    db.query.assert_not_called()


def test_get_by_ids_builds_dict_keyed_by_id():
    db = MagicMock()
    id1, id2 = uuid4(), uuid4()
    place1, place2 = MagicMock(id=id1), MagicMock(id=id2)
    db.query.return_value.filter.return_value.all.return_value = [place1, place2]
    repo = PlaceRepository(db)

    result = repo.get_by_ids([id1, id2, uuid4()])

    assert result == {id1: place1, id2: place2}


def test_get_or_create_returns_new_place_on_successful_insert():
    """INSERT ... ON CONFLICT DO NOTHING이 실제로 새 행을 반환하면(충돌 없음) 그걸 쓴다."""
    db = MagicMock()
    new_place = MagicMock(id=uuid4())
    db.execute.return_value.scalars.return_value.first.return_value = new_place
    repo = PlaceRepository(db)

    result = repo.get_or_create(
        source_type="tour_api",
        tour_content_id="126508",
        name="경복궁",
        longitude=126.977041,
        latitude=37.579617,
        area_cd="11",
        signgu_cd="11110",
    )

    assert result is new_place
    db.flush.assert_called_once()


def test_get_or_create_falls_back_to_get_by_source_on_conflict():
    """ON CONFLICT DO NOTHING이 0행을 반환하면(동시에 다른 요청이 먼저 만듦) 기존 행을 재조회한다."""
    db = MagicMock()
    db.execute.return_value.scalars.return_value.first.return_value = None
    existing_place = MagicMock(id=uuid4())
    repo = PlaceRepository(db)
    repo.get_by_source = MagicMock(return_value=existing_place)

    result = repo.get_or_create(
        source_type="tour_api",
        tour_content_id="126508",
        name="경복궁",
        longitude=126.977041,
        latitude=37.579617,
    )

    assert result is existing_place
    repo.get_by_source.assert_called_once_with("tour_api", "126508")
    db.rollback.assert_not_called()


def test_get_or_create_skips_conflict_path_for_custom_place_without_content_id():
    """tour_content_id가 없는 custom 장소는 충돌 검사 없이 바로 새로 만든다."""
    db = MagicMock()
    repo = PlaceRepository(db)
    repo.create = MagicMock(return_value=MagicMock(id=uuid4()))

    repo.get_or_create(
        source_type="custom",
        tour_content_id=None,
        name="내가 만든 장소",
        longitude=None,
        latitude=None,
    )

    repo.create.assert_called_once()
    db.execute.assert_not_called()


def test_get_or_create_normalizes_empty_string_content_id_to_none():
    """tour_content_id=""는 None과 동일하게 취급해 충돌 검사를 우회하지 않는다."""
    db = MagicMock()
    repo = PlaceRepository(db)
    repo.create = MagicMock(return_value=MagicMock(id=uuid4()))

    repo.get_or_create(
        source_type="tour_api",
        tour_content_id="",
        name="이상한 응답",
        longitude=None,
        latitude=None,
    )

    repo.create.assert_called_once_with(
        source_type="tour_api",
        tour_content_id=None,
        region_id=None,
        name="이상한 응답",
        longitude=None,
        latitude=None,
        is_recommendable=True,
        area_cd=None,
        signgu_cd=None,
    )


def test_get_or_create_backfills_existing_place_on_conflict():
    """충돌로 기존 place를 반환받을 때, 지역코드가 비어 있으면 이번 응답으로 보충한다
    (STEP6에서 처음 발견된 place가 나중에 지역코드 없이 영원히 남는 걸 방지)."""
    db = MagicMock()
    db.execute.return_value.scalars.return_value.first.return_value = None
    existing_place = MagicMock(id=uuid4())
    repo = PlaceRepository(db)
    repo.get_by_source = MagicMock(return_value=existing_place)
    repo.apply_district_code_backfill = MagicMock(return_value="updated")

    repo.get_or_create(
        source_type="tour_api",
        tour_content_id="126508",
        name="경복궁",
        longitude=126.977041,
        latitude=37.579617,
        area_cd="11",
        signgu_cd="11110",
    )

    repo.apply_district_code_backfill.assert_called_once_with(existing_place, "11", "11110")


# --- _classify_district_code_backfill (순수 함수) ---

def test_classify_backfill_missing_input_when_new_values_incomplete():
    assert _classify_district_code_backfill("11", None, None, "11110") == "missing_input"
    assert _classify_district_code_backfill(None, None, "11", None) == "missing_input"


def test_classify_backfill_updated_when_current_empty():
    assert _classify_district_code_backfill(None, None, "11", "11110") == "updated"


def test_classify_backfill_updated_when_partially_filled():
    """기존에 area_cd만 있고 signgu_cd가 없으면(부분 보충 상태) 여전히 updated다."""
    assert _classify_district_code_backfill("11", None, "11", "11110") == "updated"


def test_classify_backfill_unchanged_when_already_matches():
    assert _classify_district_code_backfill("11", "11110", "11", "11110") == "unchanged"


def test_classify_backfill_conflict_when_existing_value_differs():
    assert _classify_district_code_backfill("26", "11110", "11", "11110") == "conflict"
    assert _classify_district_code_backfill("11", "26290", "11", "11110") == "conflict"


# --- apply_district_code_backfill / preview_district_code_backfill ---

def test_get_or_create_many_returns_empty_dict_for_empty_items():
    db = MagicMock()
    repo = PlaceRepository(db)

    result = repo.get_or_create_many(source_type="tour_api", region_id=1, items=[])

    assert result == {}
    db.execute.assert_not_called()


def test_get_or_create_many_makes_one_query_and_one_insert_for_all_new_items():
    """20건을 넘겨도 SELECT 1회 + INSERT 1회로 끝나야 한다(건당 왕복 반복 금지)."""
    db = MagicMock()
    repo = PlaceRepository(db)
    repo.get_by_sources = MagicMock(return_value={})  # 아무것도 기존에 없음
    inserted = [MagicMock(id=uuid4(), tour_content_id=str(i)) for i in range(20)]
    db.execute.return_value.scalars.return_value.all.return_value = inserted

    items = [
        {
            "tour_content_id": str(i),
            "name": f"place-{i}",
            "longitude": 127.0,
            "latitude": 37.0,
            "area_cd": "11",
            "signgu_cd": "11110",
        }
        for i in range(20)
    ]
    result = repo.get_or_create_many(source_type="tour_api", region_id=1, items=items)

    assert len(result) == 20
    assert result["0"] is inserted[0]
    repo.get_by_sources.assert_called_once()  # 존재 여부 확인은 한 번의 IN 절로
    assert db.execute.call_count == 1  # INSERT도 한 번의 다중 VALUES로
    db.flush.assert_called_once()


def test_get_or_create_many_reuses_existing_place_without_inserting():
    db = MagicMock()
    repo = PlaceRepository(db)
    existing_place = MagicMock(id=uuid4())
    repo.get_by_sources = MagicMock(return_value={("tour_api", "126508"): existing_place})
    repo.apply_district_code_backfill = MagicMock()

    result = repo.get_or_create_many(
        source_type="tour_api",
        region_id=1,
        items=[
            {
                "tour_content_id": "126508",
                "name": "경복궁",
                "longitude": 126.977041,
                "latitude": 37.579617,
                "area_cd": "11",
                "signgu_cd": "11110",
            }
        ],
    )

    assert result == {"126508": existing_place}
    db.execute.assert_not_called()  # INSERT 자체가 안 나감
    repo.apply_district_code_backfill.assert_called_once_with(existing_place, "11", "11110")


def test_get_or_create_many_reselects_only_items_lost_to_a_race():
    """일부만 INSERT에서 조용히 빠지면(동시 세션이 먼저 커밋) 그 건만 재조회한다."""
    db = MagicMock()
    repo = PlaceRepository(db)
    repo.get_by_sources = MagicMock()
    repo.get_by_sources.side_effect = [
        {},  # 최초 조회: 둘 다 없음
        {("tour_api", "2"): MagicMock(id=uuid4(), tour_content_id="2")},  # raced 재조회
    ]
    inserted_place = MagicMock(id=uuid4(), tour_content_id="1")
    db.execute.return_value.scalars.return_value.all.return_value = [inserted_place]  # "2"는 raced로 빠짐
    repo.apply_district_code_backfill = MagicMock()

    items = [
        {"tour_content_id": "1", "name": "A", "longitude": None, "latitude": None, "area_cd": None, "signgu_cd": None},
        {"tour_content_id": "2", "name": "B", "longitude": None, "latitude": None, "area_cd": None, "signgu_cd": None},
    ]
    result = repo.get_or_create_many(source_type="tour_api", region_id=1, items=items)

    assert result["1"] is inserted_place
    assert result["2"].tour_content_id == "2"
    assert repo.get_by_sources.call_count == 2


def test_apply_district_code_backfill_locks_row_and_updates_when_status_updated():
    db = MagicMock()
    db.execute.return_value.one.return_value = (None, None)
    repo = PlaceRepository(db)
    place = MagicMock(id=uuid4(), area_cd=None, signgu_cd=None)

    status = repo.apply_district_code_backfill(place, "11", "11110")

    assert status == "updated"
    assert place.area_cd == "11"
    assert place.signgu_cd == "11110"
    assert db.execute.call_count == 2  # 1) FOR UPDATE 조회, 2) UPDATE
    db.flush.assert_called_once()


def test_apply_district_code_backfill_does_not_write_when_conflict():
    db = MagicMock()
    db.execute.return_value.one.return_value = ("26", "26290")
    repo = PlaceRepository(db)
    place = MagicMock(id=uuid4())

    status = repo.apply_district_code_backfill(place, "11", "11110")

    assert status == "conflict"
    assert db.execute.call_count == 1  # UPDATE는 안 나감
    db.flush.assert_not_called()


def test_apply_district_code_backfill_skips_db_entirely_when_input_incomplete():
    db = MagicMock()
    repo = PlaceRepository(db)
    place = MagicMock(id=uuid4())

    status = repo.apply_district_code_backfill(place, None, "11110")

    assert status == "missing_input"
    db.execute.assert_not_called()


def test_preview_district_code_backfill_never_writes():
    """dry-run 전용 — 어떤 경우에도 execute(UPDATE)/flush를 호출하지 않는다."""
    db = MagicMock()
    db.execute.return_value.one.return_value = (None, None)
    repo = PlaceRepository(db)

    status = repo.preview_district_code_backfill(uuid4(), "11", "11110")

    assert status == "updated"
    assert db.execute.call_count == 1  # 조회 한 번뿐, UPDATE 없음
    db.flush.assert_not_called()
