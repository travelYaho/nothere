"""TripService.get_trip_detail 을 repository mock 으로 검증한다."""
from datetime import date, time
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, ErrorCode
from app.schemas.user import CurrentUser
from app.services.trip_service import TripService


def _pref(tag_id, weight):
    p = MagicMock(experience_tag_id=tag_id, weight=weight)
    return p


def _trip_place(**overrides):
    tp = MagicMock()
    tp.id = overrides.get("id", uuid4())
    tp.place_id = overrides.get("place_id", uuid4())
    tp.position = overrides.get("position", 1)
    tp.visit_time = overrides.get("visit_time")
    tp.stay_minutes = overrides.get("stay_minutes")
    tp.is_fixed = overrides.get("is_fixed", False)
    place = MagicMock()
    place.name = overrides.get("place_name", "경복궁")
    tp.place = place
    return tp


def _current_user():
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")


def test_get_trip_detail_returns_conditions_and_places_in_order():
    service = TripService(db=MagicMock())
    service.trips = MagicMock()

    trip = MagicMock(
        id=uuid4(),
        title="2026.09.12 가족 여행",
        travel_date=date(2026, 9, 12),
        region_id=1,
        companion_type="family",
        transport_mode="walk",
        extra_time_limit_minutes=20,
        status="draft",
        current_step=3,
        needs_reanalysis=False,
    )
    trip.region.name = "서울특별시"
    trip.preferred_experiences = [_pref(6, 0.7), _pref(1, 1.0), _pref(3, 0.5)]
    trip.trip_places = [
        _trip_place(position=1, place_name="경복궁", visit_time=time(10, 0), stay_minutes=90),
        _trip_place(position=2, place_name="통인시장", stay_minutes=60),
    ]
    service.trips.get_owned_detail.return_value = trip

    result = service.get_trip_detail(_current_user(), trip.id)

    assert result.region_name == "서울특별시"
    # weight 내림차순으로 복원되어야 함: 1.0(id=1) -> 0.7(id=6) -> 0.5(id=3)
    assert result.preferred_experience_tag_ids == [1, 6, 3]
    assert [p.name for p in result.places] == ["경복궁", "통인시장"]
    assert result.places[0].visit_time == time(10, 0)
    assert result.places[0].duration_minutes == 90


def test_get_trip_detail_unknown_trip_returns_404():
    service = TripService(db=MagicMock())
    service.trips = MagicMock()
    service.trips.get_owned_detail.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.get_trip_detail(_current_user(), uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_get_trip_detail_with_no_places_returns_empty_list():
    service = TripService(db=MagicMock())
    service.trips = MagicMock()

    trip = MagicMock(
        id=uuid4(), title="t", travel_date=None, region_id=1,
        companion_type=None, transport_mode=None, extra_time_limit_minutes=None,
        status="draft", current_step=2, needs_reanalysis=False,
    )
    trip.region.name = "서울특별시"
    trip.preferred_experiences = []
    trip.trip_places = []
    service.trips.get_owned_detail.return_value = trip

    result = service.get_trip_detail(_current_user(), trip.id)

    assert result.places == []
    assert result.preferred_experience_tag_ids == []
