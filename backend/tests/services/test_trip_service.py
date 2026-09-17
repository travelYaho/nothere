"""TripService.create_trip 의 검증 규칙을 repository mock 으로 확인한다."""
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, ErrorCode
from app.schemas.trip import TripCreateRequest
from app.schemas.user import CurrentUser
from app.services.trip_service import TripService

TOMORROW = date.today() + timedelta(days=1)


def _service_with_mocks():
    service = TripService(db=MagicMock())
    service.trips = MagicMock()
    service.regions = MagicMock()
    service.experience_tags = MagicMock()
    service.regions.get_supported_by_id.return_value = MagicMock(id=1, name="서울특별시")
    service.experience_tags.get_active_by_ids.side_effect = lambda ids: list(ids)
    return service


def _current_user():
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")


@pytest.mark.parametrize("tag_ids", [[], [1], [1, 2, 3, 4], [1, 1]])
def test_invalid_preferred_experience_count_rejects_bad_counts(tag_ids):
    service = _service_with_mocks()
    payload = TripCreateRequest(
        travel_date=TOMORROW,
        region_id=1,
        preferred_experience_tag_ids=tag_ids,
    )

    with pytest.raises(AppError) as exc_info:
        service.create_trip(_current_user(), payload)

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == ErrorCode.INVALID_PREFERRED_EXPERIENCE_COUNT
    service.trips.create_trip.assert_not_called()


def test_past_travel_date_is_rejected():
    service = _service_with_mocks()
    payload = TripCreateRequest(
        travel_date=date.today() - timedelta(days=1),
        region_id=1,
        preferred_experience_tag_ids=[1, 2],
    )

    with pytest.raises(AppError) as exc_info:
        service.create_trip(_current_user(), payload)

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == ErrorCode.INVALID_TRAVEL_DATE


def test_unknown_region_returns_404():
    service = _service_with_mocks()
    service.regions.get_supported_by_id.return_value = None
    payload = TripCreateRequest(
        travel_date=TOMORROW,
        region_id=999,
        preferred_experience_tag_ids=[1, 2],
    )

    with pytest.raises(AppError) as exc_info:
        service.create_trip(_current_user(), payload)

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_unknown_experience_tag_returns_404():
    service = _service_with_mocks()
    # side_effect 가 return_value 보다 우선하므로 둘 다 덮어써야 한다.
    service.experience_tags.get_active_by_ids.side_effect = None
    service.experience_tags.get_active_by_ids.return_value = [1]  # 2개 요청했는데 1개만 존재
    payload = TripCreateRequest(
        travel_date=TOMORROW,
        region_id=1,
        preferred_experience_tag_ids=[1, 999],
    )

    with pytest.raises(AppError) as exc_info:
        service.create_trip(_current_user(), payload)

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_title_is_auto_generated_from_date_and_companion_type():
    service = _service_with_mocks()
    # 하드코딩된 과거 날짜(예: 2026-09-12)는 오늘 날짜가 그 시점을 지나면 서비스의 과거
    # 날짜 검증(INVALID_TRAVEL_DATE)에 걸려 테스트가 깨진다 — TOMORROW 기준으로 기대
    # 제목도 함께 계산해서 날짜와 무관하게 항상 성립하도록 한다.
    expected_title = f"{TOMORROW.strftime('%Y.%m.%d')} 가족 여행"
    created = MagicMock(
        id=uuid4(),
        title=expected_title,
        status="draft",
        current_step=3,
        created_at=datetime(2026, 8, 28, 10, 0, 0),
    )
    service.trips.create_trip.return_value = created

    payload = TripCreateRequest(
        title=None,
        travel_date=TOMORROW,
        region_id=1,
        companion_type="family",
        preferred_experience_tag_ids=[1, 2],
    )

    result = service.create_trip(_current_user(), payload)

    assert result.title == expected_title
    kwargs = service.trips.create_trip.call_args.kwargs
    assert kwargs["title"] == expected_title


def test_explicit_title_is_not_overwritten():
    service = _service_with_mocks()
    service.trips.create_trip.return_value = MagicMock(
        id=uuid4(), title="내 맘대로 여행", status="draft", current_step=3, created_at=datetime(2026, 8, 28, 10, 0, 0)
    )

    payload = TripCreateRequest(
        title="내 맘대로 여행",
        travel_date=TOMORROW,
        region_id=1,
        preferred_experience_tag_ids=[1, 2],
    )

    service.create_trip(_current_user(), payload)

    kwargs = service.trips.create_trip.call_args.kwargs
    assert kwargs["title"] == "내 맘대로 여행"


def test_weights_follow_click_order_1_0_7_0_5():
    service = _service_with_mocks()
    service.trips.create_trip.return_value = MagicMock(
        id=uuid4(), title="t", status="draft", current_step=3, created_at=datetime(2026, 8, 28, 10, 0, 0)
    )

    payload = TripCreateRequest(
        travel_date=TOMORROW,
        region_id=1,
        preferred_experience_tag_ids=[6, 1, 3],
    )

    service.create_trip(_current_user(), payload)

    kwargs = service.trips.create_trip.call_args.kwargs
    assert kwargs["preferred_experience_tag_ids"] == [6, 1, 3]
    assert kwargs["preferred_experience_weights"] == (1.0, 0.7, 0.5)


def _fake_trip_row(status="draft"):
    trip = MagicMock()
    trip.id = uuid4()
    trip.title = "제주도 여행"
    trip.travel_date = TOMORROW
    trip.status = status
    trip.region.name = "제주"
    return trip


def test_list_trips_maps_rows_and_forwards_filter():
    service = _service_with_mocks()
    service.trip_places = MagicMock()
    service.trip_places.count_by_trip.return_value = 2
    trip = _fake_trip_row("confirmed")
    service.trips.list_by_user.return_value = ([trip], 1)
    current_user = _current_user()

    result = service.list_trips(current_user, status_filter="confirmed", page=1)

    service.trips.list_by_user.assert_called_once_with(
        current_user.id, status_filter="confirmed", page=1
    )
    assert result.page == 1
    assert result.total_count == 1
    assert len(result.trips) == 1
    assert result.trips[0].trip_id == trip.id
    assert result.trips[0].place_count == 2
    assert result.trips[0].resume_url == f"/trips/{trip.id}/guide"


def test_list_trips_has_next_true_when_more_remain():
    service = _service_with_mocks()
    service.trip_places = MagicMock()
    service.trip_places.count_by_trip.return_value = 0
    service.trips.list_by_user.return_value = ([_fake_trip_row()], 15)

    result = service.list_trips(_current_user(), status_filter=None, page=1)

    assert result.has_next is True  # page(1) * PAGE_SIZE(10) = 10 < 15
