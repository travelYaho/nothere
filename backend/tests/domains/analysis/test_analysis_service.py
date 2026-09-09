"""AnalysisService(STEP4) 매칭/등급/파이프라인 단위 테스트."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, ErrorCode
from app.domains.analysis.service import (
    AnalysisService,
    AnalysisStatus,
    ConcentrationLevel,
    UnknownReason,
    calculate_congestion_level,
    match_concentration_spot,
    normalize_name,
)
from app.schemas.user import CurrentUser


def _user() -> CurrentUser:
    return CurrentUser(id=uuid4(), email="t@example.com", nickname="테스터", profile_image_url=None)


def _spot(name: str, normalized: str | None = None):
    return SimpleNamespace(id=1, tourist_name=name, normalized_name=normalized or normalize_name(name))


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
    svc.repo.get_trip_owned = MagicMock(return_value=SimpleNamespace(id=trip_id, places=[]))

    with pytest.raises(AppError) as exc:
        svc.run_analysis(user, trip_id)

    assert exc.value.code == ErrorCode.NO_PLACES_IN_TRIP
    assert exc.value.status_code == 422


def test_run_analysis_marks_region_not_supported_when_region_missing():
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    place_id = uuid4()
    trip_place_id = uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        region_id=None,
        travel_date=None,
        places=[SimpleNamespace(id=trip_place_id, place_id=place_id, is_fixed=False, resolution_status="pending")],
    )
    place = SimpleNamespace(id=place_id, name="이름없는장소")

    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_places_map = MagicMock(return_value={place_id: place})
    svc.repo.get_region = MagicMock(return_value=None)
    svc.repo.upsert_mapping = MagicMock()
    saved_analysis = SimpleNamespace(
        analysis_status=AnalysisStatus.UNAVAILABLE,
        level=None,
        unknown_reason=UnknownReason.REGION_NOT_SUPPORTED,
        rule_version="v1",
        analyzed_at=datetime.now(timezone.utc),
    )
    svc.repo.upsert_analysis = MagicMock(return_value=saved_analysis)
    svc.repo.get_analysis_map = MagicMock(return_value={trip_place_id: saved_analysis})

    result = svc.run_analysis(user, trip_id)

    assert result["tripId"] == str(trip_id)
    assert result["items"][0]["analysisStatus"] == AnalysisStatus.UNAVAILABLE
    assert result["items"][0]["unknownReason"] == UnknownReason.REGION_NOT_SUPPORTED
    svc.repo.upsert_mapping.assert_called_once_with(place_id, None, None, None, "no_mapping")


def test_analyze_place_uses_reviewed_mapping_without_rematching():
    """approved 매핑이 있으면 match_concentration_spot을 다시 돌리지 않고 그 결과를 그대로 쓴다."""
    db = MagicMock()
    svc = AnalysisService(db)
    trip_place = SimpleNamespace(id=uuid4(), place_id=uuid4(), is_fixed=False, resolution_status="pending")

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

    svc._analyze_place(
        trip_place,
        place_name="아무 이름",
        region_supported=True,
        api_failed=False,
        spots=decoy_spots,
        items_by_name=items_by_name,
    )

    svc.repo.upsert_mapping.assert_not_called()
    svc.repo.upsert_analysis.assert_called_once_with(
        trip_place.id, AnalysisStatus.SUCCESS, ConcentrationLevel.LOW, None, "v1"
    )


def test_analyze_place_rejected_mapping_is_treated_as_no_mapping():
    db = MagicMock()
    svc = AnalysisService(db)
    trip_place = SimpleNamespace(id=uuid4(), place_id=uuid4(), is_fixed=False, resolution_status="pending")

    rejected_mapping = SimpleNamespace(status="rejected", concentration_spot_id=None)
    svc.repo.get_mapping = MagicMock(return_value=rejected_mapping)
    svc.repo.upsert_analysis = MagicMock()
    svc.repo.upsert_mapping = MagicMock()

    svc._analyze_place(
        trip_place,
        place_name="아무 이름",
        region_supported=True,
        api_failed=False,
        spots=[_spot("아무거나")],
        items_by_name={},
    )

    svc.repo.upsert_mapping.assert_not_called()
    svc.repo.upsert_analysis.assert_called_once_with(
        trip_place.id, AnalysisStatus.UNAVAILABLE, None, UnknownReason.NO_MAPPING, "v1"
    )


def test_get_analysis_filters_crowded_only():
    db = MagicMock()
    svc = AnalysisService(db)
    user = _user()
    trip_id = uuid4()
    place_id = uuid4()
    tp_id = uuid4()

    trip = SimpleNamespace(
        id=trip_id,
        places=[SimpleNamespace(id=tp_id, place_id=place_id, is_fixed=False, resolution_status="pending")],
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
