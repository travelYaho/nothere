"""TripService.update_conditions / delete_trip 검증 규칙을 repository mock 으로 확인한다."""
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, ErrorCode
from app.schemas.trip import TripConditionsUpdateRequest
from app.schemas.user import CurrentUser
from app.services.trip_service import TripService

TOMORROW = date.today() + timedelta(days=1)


def _fake_trip(**overrides):
    trip = MagicMock()
    trip.id = overrides.get("id", uuid4())
    trip.region_id = overrides.get("region_id", 1)
    trip.travel_date = overrides.get("travel_date", TOMORROW)
    trip.transport_mode = overrides.get("transport_mode", "walk")
    trip.needs_reanalysis = overrides.get("needs_reanalysis", False)
    trip.trip_places = overrides.get("trip_places", [])
    trip.updated_at = overrides.get("updated_at", datetime(2026, 8, 28, 10, 0, 0))
    return trip


def _service_with_mocks(trip=None):
    service = TripService(db=MagicMock())
    service.trips = MagicMock()
    service.regions = MagicMock()
    service.experience_tags = MagicMock()
    service.trips.get_owned_by_id.return_value = trip if trip is not None else _fake_trip()
    service.regions.get_supported_by_id.return_value = MagicMock(id=2)
    service.experience_tags.get_active_by_ids.side_effect = lambda ids: list(ids)
    return service


def _current_user():
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")


# --- 존재하지 않거나 소유자가 다른 Trip ---

def test_update_conditions_unknown_trip_returns_404():
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.update_conditions(_current_user(), uuid4(), TripConditionsUpdateRequest(transport_mode="walk"))

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_delete_trip_unknown_trip_returns_404():
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.delete_trip(_current_user(), uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND
    service.trips.delete.assert_not_called()


def test_delete_trip_success_calls_repository_delete():
    trip = _fake_trip()
    service = _service_with_mocks(trip=trip)

    service.delete_trip(_current_user(), trip.id)

    service.trips.delete.assert_called_once_with(trip)


# --- needsReanalysis 전환 규칙 ---

def test_transport_mode_change_sets_needs_reanalysis_true():
    trip = _fake_trip(transport_mode="walk", needs_reanalysis=False)
    service = _service_with_mocks(trip=trip)
    service.trips.update_conditions.return_value = _fake_trip(needs_reanalysis=True)

    service.update_conditions(_current_user(), trip.id, TripConditionsUpdateRequest(transport_mode="public_transit"))

    kwargs = service.trips.update_conditions.call_args.kwargs
    assert kwargs["needs_reanalysis"] is True


def test_travel_date_change_sets_needs_reanalysis_true():
    trip = _fake_trip(travel_date=TOMORROW, needs_reanalysis=False)
    service = _service_with_mocks(trip=trip)
    service.trips.update_conditions.return_value = _fake_trip(needs_reanalysis=True)

    new_date = TOMORROW + timedelta(days=5)
    service.update_conditions(_current_user(), trip.id, TripConditionsUpdateRequest(travel_date=new_date))

    kwargs = service.trips.update_conditions.call_args.kwargs
    assert kwargs["needs_reanalysis"] is True


def test_unrelated_field_change_does_not_set_needs_reanalysis():
    trip = _fake_trip(needs_reanalysis=False)
    service = _service_with_mocks(trip=trip)
    service.trips.update_conditions.return_value = _fake_trip(needs_reanalysis=False)

    service.update_conditions(_current_user(), trip.id, TripConditionsUpdateRequest(extra_time_limit_minutes=30))

    kwargs = service.trips.update_conditions.call_args.kwargs
    assert kwargs["needs_reanalysis"] is False


def test_same_travel_date_resubmitted_does_not_set_needs_reanalysis():
    trip = _fake_trip(travel_date=TOMORROW, needs_reanalysis=False)
    service = _service_with_mocks(trip=trip)
    service.trips.update_conditions.return_value = _fake_trip(needs_reanalysis=False)

    service.update_conditions(_current_user(), trip.id, TripConditionsUpdateRequest(travel_date=TOMORROW))

    kwargs = service.trips.update_conditions.call_args.kwargs
    assert kwargs["needs_reanalysis"] is False


# --- regionId 변경: 자동삭제 없음 + warnings ---

def test_region_change_with_existing_places_adds_warning():
    trip = _fake_trip(region_id=1, trip_places=[MagicMock()])
    service = _service_with_mocks(trip=trip)
    service.trips.update_conditions.return_value = _fake_trip()

    result = service.update_conditions(_current_user(), trip.id, TripConditionsUpdateRequest(region_id=2))

    assert len(result.warnings) == 1
    # 기존 장소를 자동으로 지우지 않는다 — repository 호출에 삭제 관련 인자가 없다.
    service.trips.delete.assert_not_called()


def test_region_change_without_existing_places_has_no_warning():
    trip = _fake_trip(region_id=1, trip_places=[])
    service = _service_with_mocks(trip=trip)
    service.trips.update_conditions.return_value = _fake_trip()

    result = service.update_conditions(_current_user(), trip.id, TripConditionsUpdateRequest(region_id=2))

    assert result.warnings == []


def test_region_change_to_unsupported_region_returns_404():
    trip = _fake_trip(region_id=1)
    service = _service_with_mocks(trip=trip)
    service.regions.get_supported_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.update_conditions(_current_user(), trip.id, TripConditionsUpdateRequest(region_id=999))

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_region_unchanged_skips_existence_check_and_warning():
    trip = _fake_trip(region_id=1, trip_places=[MagicMock()])
    service = _service_with_mocks(trip=trip)
    service.trips.update_conditions.return_value = _fake_trip()

    result = service.update_conditions(_current_user(), trip.id, TripConditionsUpdateRequest(region_id=1))

    assert result.warnings == []
    service.regions.get_supported_by_id.assert_not_called()


# --- 선호경험 재검증 ---

@pytest.mark.parametrize("tag_ids", [[1], [1, 2, 3, 4], [1, 1]])
def test_invalid_preferred_tag_count_on_update_is_rejected(tag_ids):
    trip = _fake_trip()
    service = _service_with_mocks(trip=trip)

    with pytest.raises(AppError) as exc_info:
        service.update_conditions(
            _current_user(), trip.id, TripConditionsUpdateRequest(preferred_experience_tag_ids=tag_ids)
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == ErrorCode.INVALID_PREFERRED_EXPERIENCE_COUNT


def test_past_travel_date_on_update_is_rejected():
    trip = _fake_trip()
    service = _service_with_mocks(trip=trip)

    with pytest.raises(AppError) as exc_info:
        service.update_conditions(
            _current_user(),
            trip.id,
            TripConditionsUpdateRequest(travel_date=date.today() - timedelta(days=1)),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == ErrorCode.INVALID_TRAVEL_DATE


def test_untouched_fields_are_not_sent_to_repository():
    """exclude_unset: PATCH 요청에 없는 필드는 아예 fields 딕셔너리에 들어가지 않는다."""
    trip = _fake_trip()
    service = _service_with_mocks(trip=trip)
    service.trips.update_conditions.return_value = _fake_trip()

    service.update_conditions(_current_user(), trip.id, TripConditionsUpdateRequest(transport_mode="walk"))

    kwargs = service.trips.update_conditions.call_args.kwargs
    assert kwargs["fields"] == {"transport_mode": "walk"}
    assert kwargs["preferred_experience_tag_ids"] is None
