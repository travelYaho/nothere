"""PlaceService.remove_place_from_trip / reorder_places / update_trip_place_visit 를
repository mock 으로 검증한다.
"""
from datetime import datetime, time
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, ErrorCode
from app.schemas.place import (
    TripPlaceOrderItem,
    TripPlaceOrderUpdateRequest,
    TripPlaceVisitUpdateRequest,
)
from app.schemas.user import CurrentUser
from app.services.place_service import PlaceService


def _service_with_mocks():
    service = PlaceService(db=MagicMock())
    service.places = MagicMock()
    service.trip_places = MagicMock()
    service.trips = MagicMock()
    service.regions = MagicMock()
    return service


def _current_user():
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")


# --- remove_place_from_trip ---

def test_remove_place_success_when_above_minimum():
    service = _service_with_mocks()
    trip_place = MagicMock(id=uuid4(), trip_id=uuid4())
    service.trip_places.get_owned_by_id.return_value = trip_place
    service.trip_places.count_by_trip.return_value = 3  # 삭제해도 2개 남음

    service.remove_place_from_trip(_current_user(), trip_place.id)

    service.trip_places.delete.assert_called_once_with(trip_place)


def test_remove_last_place_returns_409_with_remaining_count():
    service = _service_with_mocks()
    trip_place = MagicMock(id=uuid4(), trip_id=uuid4())
    service.trip_places.get_owned_by_id.return_value = trip_place
    service.trip_places.count_by_trip.return_value = 1  # 삭제하면 0개

    with pytest.raises(AppError) as exc_info:
        service.remove_place_from_trip(_current_user(), trip_place.id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == ErrorCode.MINIMUM_PLACES_REQUIRED
    assert exc_info.value.extra == {"remainingCount": 0}
    service.trip_places.delete.assert_not_called()


def test_remove_place_unknown_returns_404():
    service = _service_with_mocks()
    service.trip_places.get_owned_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.remove_place_from_trip(_current_user(), uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


# --- reorder_places ---

def test_reorder_places_success_marks_needs_reanalysis():
    service = _service_with_mocks()
    trip_id = uuid4()
    tp1, tp2 = uuid4(), uuid4()
    trip = MagicMock(id=trip_id)
    service.trips.get_owned_by_id.return_value = trip
    service.trip_places.get_owned_by_ids.return_value = [MagicMock(), MagicMock()]
    service.trips.mark_needs_reanalysis.return_value = MagicMock(
        id=trip_id, needs_reanalysis=True, updated_at=datetime(2026, 1, 1)
    )

    payload = TripPlaceOrderUpdateRequest(
        order=[
            TripPlaceOrderItem(trip_place_id=tp1, visit_order=1),
            TripPlaceOrderItem(trip_place_id=tp2, visit_order=2),
        ]
    )
    result = service.reorder_places(_current_user(), trip_id, payload)

    assert result.needs_reanalysis is True
    service.trip_places.reorder.assert_called_once_with({tp1: 1, tp2: 2})
    service.trips.mark_needs_reanalysis.assert_called_once_with(trip)


def test_reorder_places_unknown_trip_returns_404():
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = None

    payload = TripPlaceOrderUpdateRequest(order=[TripPlaceOrderItem(trip_place_id=uuid4(), visit_order=1)])
    with pytest.raises(AppError) as exc_info:
        service.reorder_places(_current_user(), uuid4(), payload)

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_reorder_places_with_foreign_trip_place_id_returns_404():
    """다른 여행의 tripPlaceId 가 섞여 있으면 404 — get_owned_by_ids 결과 개수가 덜 나온다."""
    service = _service_with_mocks()
    trip_id = uuid4()
    service.trips.get_owned_by_id.return_value = MagicMock(id=trip_id)
    service.trip_places.get_owned_by_ids.return_value = [MagicMock()]  # 요청은 2개, 조회는 1개

    payload = TripPlaceOrderUpdateRequest(
        order=[
            TripPlaceOrderItem(trip_place_id=uuid4(), visit_order=1),
            TripPlaceOrderItem(trip_place_id=uuid4(), visit_order=2),
        ]
    )
    with pytest.raises(AppError) as exc_info:
        service.reorder_places(_current_user(), trip_id, payload)

    assert exc_info.value.status_code == 404
    service.trip_places.reorder.assert_not_called()


# --- update_trip_place_visit ---

def test_update_visit_time_and_duration_does_not_change_needs_reanalysis():
    service = _service_with_mocks()
    trip_place_id = uuid4()
    fake_trip = MagicMock(needs_reanalysis=False)
    updated = MagicMock(
        id=trip_place_id,
        visit_time=time(10, 0),
        stay_minutes=60,
        is_fixed=False,
        updated_at=datetime(2026, 1, 1),
        trip=fake_trip,
    )
    service.trip_places.get_owned_by_id.return_value = MagicMock()
    service.trip_places.update_visit.return_value = updated

    payload = TripPlaceVisitUpdateRequest(visit_time=time(10, 0), duration_minutes=60)
    result = service.update_trip_place_visit(_current_user(), trip_place_id, payload)

    assert result.needs_reanalysis is False
    assert result.duration_minutes == 60


def test_update_is_fixed_also_does_not_change_needs_reanalysis():
    """isFixed 영향 여부는 명세서에서도 미정 — 보수적으로 unchanged 로 처리."""
    service = _service_with_mocks()
    trip_place_id = uuid4()
    fake_trip = MagicMock(needs_reanalysis=False)
    updated = MagicMock(
        id=trip_place_id,
        visit_time=None,
        stay_minutes=None,
        is_fixed=True,
        updated_at=datetime(2026, 1, 1),
        trip=fake_trip,
    )
    service.trip_places.get_owned_by_id.return_value = MagicMock()
    service.trip_places.update_visit.return_value = updated

    payload = TripPlaceVisitUpdateRequest(is_fixed=True)
    result = service.update_trip_place_visit(_current_user(), trip_place_id, payload)

    assert result.needs_reanalysis is False
    assert result.is_fixed is True


def test_update_visit_unknown_trip_place_returns_404():
    service = _service_with_mocks()
    service.trip_places.get_owned_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.update_trip_place_visit(_current_user(), uuid4(), TripPlaceVisitUpdateRequest(is_fixed=True))

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_update_visit_only_touches_provided_fields():
    service = _service_with_mocks()
    trip_place_id = uuid4()
    service.trip_places.get_owned_by_id.return_value = MagicMock()
    service.trip_places.update_visit.return_value = MagicMock(
        id=trip_place_id, visit_time=None, stay_minutes=None, is_fixed=False,
        updated_at=datetime(2026, 1, 1), trip=MagicMock(needs_reanalysis=False),
    )

    service.update_trip_place_visit(_current_user(), trip_place_id, TripPlaceVisitUpdateRequest(is_fixed=False))

    kwargs = service.trip_places.update_visit.call_args.kwargs
    assert kwargs["fields"] == {"is_fixed": False}
