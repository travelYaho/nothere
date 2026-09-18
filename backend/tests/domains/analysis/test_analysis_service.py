"""AnalysisService(STEP4) 매칭/등급/파이프라인 단위 테스트."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.clients.concentration_api import ConcentrationItem
from app.core.exceptions import AppError, ErrorCode
from app.domains.analysis.service import (
    AnalysisService,
    AnalysisStatus,
    ConcentrationLevel,
    UnknownReason,
    calculate_congestion_level,
    get_spots_and_items_for_codes,
    match_concentration_spot,
    normalize_name,
)
from app.schemas.user import CurrentUser


def _user() -> CurrentUser:
    return CurrentUser(id=uuid4(), email="t@example.com", nickname="테스터", profile_image_url=None)


def _spot(name: str, normalized: str | None = None, area_cd: str = "11", signgu_cd: str = "11110"):
    return SimpleNamespace(
        id=1,
        tourist_name=name,
        normalized_name=normalized or normalize_name(name),
        area_cd=area_cd,
        signgu_cd=signgu_cd,
    )


def test_calculate_congestion_level_uses_cutoffs():
    assert calculate_congestion_level(10.0) == ConcentrationLevel.LOW
    assert calculate_congestion_level(70.0) == ConcentrationLevel.MID
    assert calculate_congestion_level(95.0) == ConcentrationLevel.HIGH


def test_match_concentration_spot_exact_single():
    spots = [_spot("경복궁"), _spot("창덕궁")]
    result = match_concentration_spot("경복궁", spots)
    assert result.spot.tourist_name == "경복궁"
    assert result.match_method == "exact"
    assert result.status == "auto_approved"


def test_match_concentration_spot_no_candidates_is_no_mapping():
    result = match_concentration_spot("아무데나", [])
    assert result.spot is None
    assert result.status == "no_mapping"


def test_match_concentration_spot_fuzzy_requires_review():
    spots = [_spot("경복궁")]
    result = match_concentration_spot("경복궁전", spots)
    assert result.spot is not None
    assert result.match_method == "fuzzy"
    assert result.status == "review_required"


def test_run_analysis_raises_when_trip_empty():
    db = MagicMock()
    svc = AnalysisService(db)
    trip_id = uuid4()
    user = _user()
    svc.repo.get_trip_owned = MagicMock(return_value=SimpleNamespace(id=trip_id, trip_places=[]))

    with pytest.raises(AppError) as exc:
        svc.run_analysis(user, trip_id)

    assert exc.value.code == ErrorCode.NO_PLACES_IN_TRIP
    assert exc.value.status_code == 422


def test_run_analysis_marks_no_district_code_when_place_missing_codes():
    """place에 area_cd/signgu_cd가 없으면(예: 커스텀 장소) 그 장소만 분석 불가 처리한다."""
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    place_id = uuid4()
    trip_place_id = uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        travel_date=None,
        trip_places=[
            SimpleNamespace(
                id=trip_place_id,
                place_id=place_id,
                is_fixed=False,
                resolution_status="pending",
                visit_time=None,
            )
        ],
    )
    place = SimpleNamespace(id=place_id, name="이름없는장소", area_cd=None, signgu_cd=None)

    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(return_value={place_id: place})
    svc.repo.upsert_mapping = MagicMock()
    saved_analysis = SimpleNamespace(
        analysis_status=AnalysisStatus.UNAVAILABLE,
        level=None,
        unknown_reason=UnknownReason.NO_DISTRICT_CODE,
        rule_version="v1",
        analyzed_at=datetime.now(timezone.utc),
    )
    svc.repo.upsert_analysis = MagicMock(return_value=saved_analysis)
    svc.repo.get_analysis_map = MagicMock(return_value={trip_place_id: saved_analysis})

    result = svc.run_analysis(user, trip_id)

    assert result["tripId"] == str(trip_id)
    assert result["items"][0]["analysisStatus"] == AnalysisStatus.UNAVAILABLE
    assert result["items"][0]["unknownReason"] == UnknownReason.NO_DISTRICT_CODE
    svc.repo.upsert_mapping.assert_called_once_with(place_id, None, None, None, "no_mapping")


def test_run_analysis_skips_successful_places_unless_needs_reanalysis():
    """교체 후 부분 재분석 시 이미 성공한 장소는 다시 돌리지 않아 다른 장소 혼잡도가 유지된다."""
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    kept_place_id, missing_place_id = uuid4(), uuid4()
    kept_tp_id, missing_tp_id = uuid4(), uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        travel_date=None,
        needs_reanalysis=False,
        trip_places=[
            SimpleNamespace(
                id=kept_tp_id, place_id=kept_place_id, is_fixed=False,
                resolution_status="pending", visit_time=None,
            ),
            SimpleNamespace(
                id=missing_tp_id, place_id=missing_place_id, is_fixed=False,
                resolution_status="pending", visit_time=None,
            ),
        ],
    )
    kept_place = SimpleNamespace(id=kept_place_id, name="유지장소", area_cd="11", signgu_cd="11110")
    missing_place = SimpleNamespace(
        id=missing_place_id, name="새장소", area_cd=None, signgu_cd=None,
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(
        return_value={kept_place_id: kept_place, missing_place_id: missing_place}
    )
    svc.repo.upsert_mapping = MagicMock()
    svc.repo.upsert_analysis = MagicMock(
        return_value=SimpleNamespace(
            analysis_status=AnalysisStatus.UNAVAILABLE, level=None,
            unknown_reason=UnknownReason.NO_DISTRICT_CODE, rule_version="v1",
            analyzed_at=datetime.now(timezone.utc),
        )
    )
    svc.repo.get_analysis_map = MagicMock(
        return_value={
            kept_tp_id: SimpleNamespace(
                analysis_status=AnalysisStatus.SUCCESS, level=ConcentrationLevel.HIGH,
            ),
            missing_tp_id: None,
        }
    )
    svc.get_analysis = MagicMock(
        return_value={"tripId": str(trip_id), "items": []}
    )

    svc.run_analysis(user, trip_id)

    svc.repo.upsert_analysis.assert_called_once_with(
        missing_tp_id, AnalysisStatus.UNAVAILABLE, None, UnknownReason.NO_DISTRICT_CODE, "v1"
    )


def test_run_analysis_keeps_needs_reanalysis_when_later_place_fails():
    """첫 장소 upsert가 commit돼도 다음 장소가 실패하면 needs_reanalysis는 그대로 True다."""
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    first_place_id, second_place_id = uuid4(), uuid4()
    first_tp_id, second_tp_id = uuid4(), uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        travel_date=None,
        needs_reanalysis=True,
        trip_places=[
            SimpleNamespace(
                id=first_tp_id, place_id=first_place_id, is_fixed=False,
                resolution_status="pending", visit_time=None,
            ),
            SimpleNamespace(
                id=second_tp_id, place_id=second_place_id, is_fixed=False,
                resolution_status="pending", visit_time=None,
            ),
        ],
    )
    first_place = SimpleNamespace(id=first_place_id, name="첫장소", area_cd=None, signgu_cd=None)
    second_place = SimpleNamespace(id=second_place_id, name="둘째장소", area_cd=None, signgu_cd=None)
    saved = SimpleNamespace(
        analysis_status=AnalysisStatus.UNAVAILABLE, level=None,
        unknown_reason=UnknownReason.NO_DISTRICT_CODE, rule_version="v1",
        analyzed_at=datetime.now(timezone.utc),
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(
        return_value={first_place_id: first_place, second_place_id: second_place}
    )
    svc.repo.upsert_mapping = MagicMock()
    svc.repo.upsert_analysis = MagicMock(side_effect=[saved, SQLAlchemyError("second place failed")])

    with pytest.raises(AppError) as exc:
        svc.run_analysis(user, trip_id)

    assert exc.value.code == ErrorCode.DB_ERROR
    assert trip.needs_reanalysis is True


def test_run_analysis_clears_needs_reanalysis_only_after_full_success():
    """모든 장소 분석과 get_analysis()가 끝난 뒤에만 플래그를 끈다."""
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    place_id = uuid4()
    trip_place_id = uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        travel_date=None,
        needs_reanalysis=True,
        trip_places=[
            SimpleNamespace(
                id=trip_place_id, place_id=place_id, is_fixed=False,
                resolution_status="pending", visit_time=None,
            )
        ],
    )
    place = SimpleNamespace(id=place_id, name="이름없는장소", area_cd=None, signgu_cd=None)
    saved = SimpleNamespace(
        analysis_status=AnalysisStatus.UNAVAILABLE, level=None,
        unknown_reason=UnknownReason.NO_DISTRICT_CODE, rule_version="v1",
        analyzed_at=datetime.now(timezone.utc),
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(return_value={place_id: place})
    svc.repo.upsert_mapping = MagicMock()
    svc.repo.upsert_analysis = MagicMock(return_value=saved)
    svc.get_analysis = MagicMock(return_value={"tripId": str(trip_id), "items": []})

    svc.run_analysis(user, trip_id)

    assert trip.needs_reanalysis is False
    db.commit.assert_called()


def test_analyze_place_uses_reviewed_mapping_without_rematching():
    """approved 매핑이 있으면 match_concentration_spot을 다시 돌리지 않고 그 결과를 그대로 쓴다."""
    db = MagicMock()
    svc = AnalysisService(db)
    trip_place = SimpleNamespace(id=uuid4(), place_id=uuid4(), is_fixed=False, resolution_status="pending")
    place = SimpleNamespace(name="아무 이름", area_cd="11", signgu_cd="11110")

    approved_spot = _spot("실제승인된장소")
    reviewed_mapping = SimpleNamespace(status="approved", concentration_spot_id=approved_spot.id)

    svc.repo.get_mapping = MagicMock(return_value=reviewed_mapping)
    svc.repo.get_spot = MagicMock(return_value=approved_spot)
    svc.repo.upsert_analysis = MagicMock()
    svc.repo.upsert_mapping = MagicMock()

    # 자동 매칭이 실제로는 완전히 다른(틀린) 장소를 골라도, 리뷰된 매핑이 있으면 이 결과는
    # 쓰이지 않아야 한다 — 만약 이 spots를 썼다면 아래 assert에서 다른 값이 저장됐을 것이다.
    decoy_spots = [_spot("자동매칭이_고른_엉뚱한장소")]
    items_by_name = {"실제승인된장소": SimpleNamespace(raw_value=10.0, base_ymd="20260910")}
    region_cache = {("11", "11110"): (decoy_spots, items_by_name, False)}

    svc._analyze_place(trip_place, place, travel_date=None, region_cache=region_cache)

    svc.repo.upsert_mapping.assert_not_called()
    svc.repo.upsert_analysis.assert_called_once_with(
        trip_place.id, AnalysisStatus.SUCCESS, ConcentrationLevel.LOW, None, "v1"
    )


def test_analyze_place_reviewed_mapping_with_district_mismatch_is_flagged_for_review():
    """승인된 매핑이 가리키는 spot의 구와 place의 현재 구가 다르면(동명이인 관광지가 다른
    구에 있을 수 있음) 등급을 계산하지 않고 재검수 필요로 표시한다 — 매핑 레코드 자체는
    건드리지 않는다(코드 리뷰로 발견, 2026-09-14)."""
    db = MagicMock()
    svc = AnalysisService(db)
    trip_place = SimpleNamespace(id=uuid4(), place_id=uuid4(), is_fixed=False, resolution_status="pending")
    place = SimpleNamespace(name="아무 이름", area_cd="11", signgu_cd="11110")

    # 승인된 spot은 다른 구(26/26290) 소속인데 place는 11/11110 — 이름은 같아도 다른 구.
    mismatched_spot = _spot("동명이인장소", area_cd="26", signgu_cd="26290")
    reviewed_mapping = SimpleNamespace(status="approved", concentration_spot_id=mismatched_spot.id)

    svc.repo.get_mapping = MagicMock(return_value=reviewed_mapping)
    svc.repo.get_spot = MagicMock(return_value=mismatched_spot)
    svc.repo.upsert_analysis = MagicMock()
    svc.repo.upsert_mapping = MagicMock()

    items_by_name = {"동명이인장소": SimpleNamespace(raw_value=10.0, base_ymd="20260910")}
    region_cache = {("11", "11110"): ([mismatched_spot], items_by_name, False)}

    svc._analyze_place(trip_place, place, travel_date=None, region_cache=region_cache)

    # 매핑 레코드는 자동으로 건드리지 않는다(삭제/상태변경 없음).
    svc.repo.upsert_mapping.assert_not_called()
    svc.repo.upsert_analysis.assert_called_once_with(
        trip_place.id, AnalysisStatus.UNAVAILABLE, None, UnknownReason.MAPPING_PENDING, "v1"
    )


def test_analyze_place_rejected_mapping_is_treated_as_no_mapping():
    db = MagicMock()
    svc = AnalysisService(db)
    trip_place = SimpleNamespace(id=uuid4(), place_id=uuid4(), is_fixed=False, resolution_status="pending")
    place = SimpleNamespace(name="아무 이름", area_cd="11", signgu_cd="11110")

    rejected_mapping = SimpleNamespace(status="rejected", concentration_spot_id=None)
    svc.repo.get_mapping = MagicMock(return_value=rejected_mapping)
    svc.repo.upsert_analysis = MagicMock()
    svc.repo.upsert_mapping = MagicMock()

    region_cache = {("11", "11110"): ([_spot("아무거나")], {}, False)}
    svc._analyze_place(trip_place, place, travel_date=None, region_cache=region_cache)

    svc.repo.upsert_mapping.assert_not_called()
    svc.repo.upsert_analysis.assert_called_once_with(
        trip_place.id, AnalysisStatus.UNAVAILABLE, None, UnknownReason.NO_MAPPING, "v1"
    )


def test_run_analysis_caches_district_lookup_across_places_in_same_district(monkeypatch):
    """같은 (area_cd, signgu_cd)를 가진 place 두 개가 있으면 집중률 API를 한 번만 호출한다."""
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    place_id_1, place_id_2 = uuid4(), uuid4()
    tp_id_1, tp_id_2 = uuid4(), uuid4()

    place_1 = SimpleNamespace(id=place_id_1, name="장소1", area_cd="11", signgu_cd="11110")
    place_2 = SimpleNamespace(id=place_id_2, name="장소2", area_cd="11", signgu_cd="11110")
    trip = SimpleNamespace(
        id=trip_id,
        travel_date=None,
        trip_places=[
            SimpleNamespace(id=tp_id_1, place_id=place_id_1, is_fixed=False, resolution_status="pending", visit_time=None),
            SimpleNamespace(id=tp_id_2, place_id=place_id_2, is_fixed=False, resolution_status="pending", visit_time=None),
        ],
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(return_value={place_id_1: place_1, place_id_2: place_2})
    svc.repo.get_mapping = MagicMock(return_value=None)
    svc.repo.upsert_mapping = MagicMock()
    svc.repo.upsert_analysis = MagicMock(
        return_value=SimpleNamespace(
            analysis_status="unavailable", level=None, unknown_reason="no_mapping",
            rule_version="v1", analyzed_at=None,
        )
    )
    svc.repo.get_analysis_map = MagicMock(return_value={})

    call_count = {"n": 0}

    def fake_get_spots_and_items_for_codes(repo, area_cd, signgu_cd, travel_date):
        call_count["n"] += 1
        return [], {}, False

    monkeypatch.setattr(
        "app.domains.analysis.service.get_spots_and_items_for_codes",
        fake_get_spots_and_items_for_codes,
    )

    svc.run_analysis(user, trip_id)

    assert call_count["n"] == 1


def test_run_analysis_isolates_failure_to_places_sharing_the_failed_district(monkeypatch):
    """구 하나의 집중률 API 호출이 실패하면, 그 구를 공유하는 장소들은 함께 failed가 되고
    다른 구의 장소는 영향 없이 정상 분석된다 — "장소 하나만"이 아니라 "같은 구 전체"가 맞는
    경계다(요청 하나 안에서 구 단위로 API 응답을 공유하는 캐시 설계이므로)."""
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()

    place_a1 = uuid4()  # 구 A, 실패
    place_a2 = uuid4()  # 구 A, 실패(같은 구를 공유해서 함께 실패)
    place_b1 = uuid4()  # 구 B, 정상
    tp_a1, tp_a2, tp_b1 = uuid4(), uuid4(), uuid4()

    places_map = {
        place_a1: SimpleNamespace(id=place_a1, name="장소A1", area_cd="11", signgu_cd="11110"),
        place_a2: SimpleNamespace(id=place_a2, name="장소A2", area_cd="11", signgu_cd="11110"),
        place_b1: SimpleNamespace(id=place_b1, name="장소B1", area_cd="11", signgu_cd="11140"),
    }
    trip = SimpleNamespace(
        id=trip_id,
        travel_date=None,
        trip_places=[
            SimpleNamespace(id=tp_a1, place_id=place_a1, is_fixed=False, resolution_status="pending", visit_time=None),
            SimpleNamespace(id=tp_a2, place_id=place_a2, is_fixed=False, resolution_status="pending", visit_time=None),
            SimpleNamespace(id=tp_b1, place_id=place_b1, is_fixed=False, resolution_status="pending", visit_time=None),
        ],
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(return_value=places_map)
    svc.repo.get_mapping = MagicMock(return_value=None)
    svc.repo.upsert_mapping = MagicMock()

    saved: dict[UUID, str] = {}

    def fake_upsert_analysis(trip_place_id, analysis_status, level, unknown_reason, rule_version):
        saved[trip_place_id] = analysis_status
        return SimpleNamespace(
            analysis_status=analysis_status, level=level, unknown_reason=unknown_reason,
            rule_version=rule_version, analyzed_at=None,
        )

    svc.repo.upsert_analysis = MagicMock(side_effect=fake_upsert_analysis)
    svc.repo.get_analysis_map = MagicMock(return_value={})

    def fake_get_spots_and_items_for_codes(repo, area_cd, signgu_cd, travel_date):
        if signgu_cd == "11110":  # 구 A만 API 실패
            return [], {}, True
        return [], {}, False  # 구 B는 정상이지만 매칭 실패(no_mapping) — 크래시만 아니면 됨

    monkeypatch.setattr(
        "app.domains.analysis.service.get_spots_and_items_for_codes",
        fake_get_spots_and_items_for_codes,
    )

    svc.run_analysis(user, trip_id)

    assert saved[tp_a1] == AnalysisStatus.FAILED
    assert saved[tp_a2] == AnalysisStatus.FAILED
    assert saved[tp_b1] != AnalysisStatus.FAILED


# --- get_spots_and_items_for_codes: N+1 DB 왕복 제거 + 지역코드 검증 (2026-09-13) ---

def test_get_spots_and_items_for_codes_dedups_same_spot_across_dates(monkeypatch):
    """같은 관광지가 30일치처럼 여러 날짜로 중복 응답돼도 bulk_upsert_spots는 이름 기준으로
    한 번만 부른다 — 예전엔 행마다 DB에 물어봐서 응답이 수천 행이면 DB 왕복도 그만큼이었다."""
    items = [
        ConcentrationItem(tourist_name="경국사", area_cd="11", signgu_cd="11290", base_ymd="20260101", raw_value=10.0),
        ConcentrationItem(tourist_name="경국사", area_cd="11", signgu_cd="11290", base_ymd="20260102", raw_value=90.0),
        ConcentrationItem(tourist_name="경국사", area_cd="11", signgu_cd="11290", base_ymd="20260103", raw_value=50.0),
    ]
    monkeypatch.setattr(
        "app.domains.analysis.service.fetch_concentration", lambda area_cd, signgu_cd: items
    )
    repo = MagicMock()
    repo.bulk_upsert_spots = MagicMock(return_value=[_spot("경국사")])

    spots, items_by_name, api_failed = get_spots_and_items_for_codes(
        repo, "11", "11290", travel_date=date(2026, 1, 2)
    )

    assert api_failed is False
    repo.bulk_upsert_spots.assert_called_once_with(
        "11", "11290", [("경국사", normalize_name("경국사"))]
    )
    assert items_by_name["경국사"].raw_value == 90.0  # travel_date(01-02)에 해당하는 값만 선택


def test_get_spots_and_items_for_codes_fails_whole_district_on_region_mismatch(monkeypatch):
    """응답 item의 지역코드가 요청과 다르면 그 항목만 조용히 빼지 않고 이 시군구 조회
    전체를 실패로 처리한다 — 현재 지역에 동명 관광지가 이미 있으면 다른 지역 값이 섞여
    들어갈 수 있어서, 부분적으로 걸러내는 대신 확실하게 실패시킨다."""
    items = [
        ConcentrationItem(tourist_name="정상장소", area_cd="11", signgu_cd="11290", base_ymd="20260101", raw_value=10.0),
        ConcentrationItem(tourist_name="다른지역장소", area_cd="26", signgu_cd="26290", base_ymd="20260101", raw_value=20.0),
    ]
    monkeypatch.setattr(
        "app.domains.analysis.service.fetch_concentration", lambda area_cd, signgu_cd: items
    )
    repo = MagicMock()

    result = get_spots_and_items_for_codes(repo, "11", "11290")

    assert result == ([], {}, True)
    repo.bulk_upsert_spots.assert_not_called()


def test_run_analysis_logs_failure_time_when_response_construction_fails(monkeypatch, caplog):
    """분석 루프가 아니라 get_analysis()(응답 구성) 단계에서 실패해도 실패 시각 로그가
    남아야 한다 — try가 분석 루프만 감싸면 이 경로는 로그 없이 그대로 새어나간다
    (2026-09-13 피드백으로 발견한 로그 공백)."""
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    place_id, tp_id = uuid4(), uuid4()

    place = SimpleNamespace(id=place_id, name="장소", area_cd="11", signgu_cd="11110")
    trip = SimpleNamespace(
        id=trip_id,
        travel_date=None,
        trip_places=[
            SimpleNamespace(
                id=tp_id, place_id=place_id, is_fixed=False,
                resolution_status="pending", visit_time=None,
            ),
        ],
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(return_value={place_id: place})
    svc.repo.get_mapping = MagicMock(return_value=None)
    svc.repo.upsert_mapping = MagicMock()
    svc.repo.upsert_analysis = MagicMock(
        return_value=SimpleNamespace(
            analysis_status="unavailable", level=None, unknown_reason="no_mapping",
            rule_version="v1", analyzed_at=None,
        )
    )
    monkeypatch.setattr(
        "app.domains.analysis.service.get_spots_and_items_for_codes",
        lambda repo, area_cd, signgu_cd, travel_date: ([], {}, False),
    )
    svc.get_analysis = MagicMock(side_effect=RuntimeError("응답 구성 중 DB 오류"))

    with caplog.at_level("ERROR", logger="yeogimalgo.analysis"):
        with pytest.raises(RuntimeError):
            svc.run_analysis(user, trip_id)

    assert any("run_analysis 실패" in record.message for record in caplog.records)


def test_get_analysis_filters_crowded_only():
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    place_id = uuid4()
    tp_id = uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        trip_places=[
            SimpleNamespace(
                id=tp_id,
                place_id=place_id,
                is_fixed=False,
                resolution_status="pending",
                visit_time=time(10, 30),
            )
        ],
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(return_value={place_id: SimpleNamespace(name="종묘")})
    svc.repo.get_analysis_map = MagicMock(
        return_value={
            tp_id: SimpleNamespace(
                analysis_status="success",
                level="high",
                unknown_reason=None,
                rule_version="v1",
                analyzed_at=datetime.now(timezone.utc),
            )
        }
    )

    result = svc.get_analysis(user, trip_id, status_filter="CROWDED")
    assert result["highConcentrationCount"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["level"] == "high"
    assert result["items"][0]["visitTime"] == "10:30"


def test_get_analysis_does_not_default_unknown_reason_to_no_district_code_when_never_analyzed():
    """analysis 레코드가 아예 없는 건 "아직 분석 안 함"이지 "지역코드 없음"이 아니다 —
    place에 유효한 area_cd/signgu_cd가 있어도 run_analysis()를 한 번도 안 돌렸으면
    unknownReason을 NO_DISTRICT_CODE로 단정하지 않는다(코드 리뷰로 발견한 오분류,
    2026-09-14)."""
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    place_id = uuid4()
    tp_id = uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        trip_places=[
            SimpleNamespace(
                id=tp_id, place_id=place_id, is_fixed=False,
                resolution_status="pending", visit_time=None,
            )
        ],
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(
        return_value={place_id: SimpleNamespace(name="경국사", area_cd="11", signgu_cd="11290")}
    )
    svc.repo.get_analysis_map = MagicMock(return_value={})  # 분석 레코드 자체가 없음

    result = svc.get_analysis(user, trip_id, status_filter=None)

    assert result["items"][0]["analysisStatus"] == AnalysisStatus.UNAVAILABLE
    assert result["items"][0]["unknownReason"] is None


def test_get_analysis_visit_time_is_null_when_not_set():
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    place_id = uuid4()
    tp_id = uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        trip_places=[
            SimpleNamespace(
                id=tp_id,
                place_id=place_id,
                is_fixed=False,
                resolution_status="pending",
                visit_time=None,
            )
        ],
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(return_value={place_id: SimpleNamespace(name="종묘")})
    svc.repo.get_analysis_map = MagicMock(return_value={})

    result = svc.get_analysis(user, trip_id, status_filter=None)
    assert result["items"][0]["visitTime"] is None
    assert result["items"][0]["wasReplaced"] is False
    assert result["items"][0]["replacedFrom"] is None


def test_get_analysis_includes_replaced_from_when_active_replacement_exists():
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    from_place_id = uuid4()
    to_place_id = uuid4()
    tp_id = uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        trip_places=[
            SimpleNamespace(
                id=tp_id,
                place_id=to_place_id,
                is_fixed=False,
                resolution_status="replaced",
                visit_time=time(10, 0),
            )
        ],
    )
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_active_replacements_map = MagicMock(
        return_value={tp_id: SimpleNamespace(from_place_id=from_place_id)}
    )
    svc.repo.get_places_map = MagicMock(
        return_value={
            to_place_id: SimpleNamespace(name="서울한방진흥센터 일대"),
            from_place_id: SimpleNamespace(name="경복궁"),
        }
    )
    svc.repo.get_analysis_map = MagicMock(
        return_value={
            tp_id: SimpleNamespace(
                analysis_status="success",
                level="low",
                unknown_reason=None,
                rule_version="v1",
                analyzed_at=datetime.now(timezone.utc),
            )
        }
    )

    result = svc.get_analysis(user, trip_id, status_filter=None)
    item = result["items"][0]
    assert item["wasReplaced"] is True
    assert item["replacedFrom"] == "경복궁"
    assert item["placeName"] == "서울한방진흥센터 일대"
    assert item["resolutionStatus"] == "replaced"
