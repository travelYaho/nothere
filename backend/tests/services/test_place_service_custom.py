"""PlaceService.add_custom_place_to_trip 을 repository/Kakao mock 으로 검증한다."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.clients.kakao_api import GeocodedAddress
from app.core.exceptions import AppError, ErrorCode
from app.schemas.place import CustomPlaceAddRequest
from app.schemas.user import CurrentUser
from app.services.place_service import PlaceService


def _tag(tag_id, name):
    t = MagicMock(id=tag_id)
    t.name = name
    return t


def _service_with_mocks():
    service = PlaceService(db=MagicMock())
    service.places = MagicMock()
    service.trip_places = MagicMock()
    service.trips = MagicMock()
    service.regions = MagicMock()
    service.experience_tags = MagicMock()
    return service


def _current_user():
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")


def _payload(**overrides):
    defaults = dict(
        name="유성푸르지오시티",
        category_tag_id=2,
        address="서울 종로구 사직로 161",
        expected_wait_minutes=60,
    )
    defaults.update(overrides)
    return CustomPlaceAddRequest(**defaults)


def test_add_custom_place_success():
    service = _service_with_mocks()
    trip_id = uuid4()
    place_id = uuid4()
    trip = MagicMock(id=trip_id, region_id=1)
    service.trips.get_owned_by_id.return_value = trip
    service.experience_tags.get_active_by_ids.return_value = [_tag(2, "역사·문화")]
    created_place = MagicMock(id=place_id)
    created_place.name = "유성푸르지오시티"
    service.places.create.return_value = created_place
    service.trip_places.next_position.return_value = 5
    service.trip_places.add.return_value = MagicMock(
        id=uuid4(), trip_id=trip_id, position=5, is_fixed=False
    )

    with patch(
        "app.services.place_service.kakao_api.geocode_address",
        return_value=GeocodedAddress(latitude=37.57, longitude=126.97),
    ) as mock_geocode:
        result = service.add_custom_place_to_trip(_current_user(), trip_id, _payload())

    mock_geocode.assert_called_once_with("서울 종로구 사직로 161")
    service.places.create.assert_called_once_with(
        source_type="custom",
        tour_content_id=None,
        region_id=1,
        name="유성푸르지오시티",
        longitude=126.97,
        latitude=37.57,
        is_recommendable=False,
        expected_wait_minutes=60,
    )
    service.places.add_experience_tag.assert_called_once_with(place_id, 2)
    assert result.visit_order == 5
    assert result.category == "역사·문화"


def test_add_custom_place_unknown_trip_returns_404():
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.add_custom_place_to_trip(_current_user(), uuid4(), _payload())

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_add_custom_place_unknown_category_returns_404():
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = MagicMock(id=uuid4(), region_id=1)
    service.experience_tags.get_active_by_ids.return_value = []

    with pytest.raises(AppError) as exc_info:
        service.add_custom_place_to_trip(_current_user(), uuid4(), _payload(category_tag_id=999))

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND
    service.places.create.assert_not_called()


def test_add_custom_place_unresolvable_address_returns_400():
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = MagicMock(id=uuid4(), region_id=1)
    service.experience_tags.get_active_by_ids.return_value = [_tag(2, "역사·문화")]

    with patch("app.services.place_service.kakao_api.geocode_address", return_value=None):
        with pytest.raises(AppError) as exc_info:
            service.add_custom_place_to_trip(_current_user(), uuid4(), _payload(address="asdkjaslkdjas"))

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == ErrorCode.ADDRESS_NOT_FOUND
    service.places.create.assert_not_called()


def test_add_custom_place_geocoding_service_down_propagates_503():
    """Kakao 자체가 죽었을 때(EXTERNAL_API_UNAVAILABLE)는 주소를 못 찾은 것과 구분되어야 한다."""
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = MagicMock(id=uuid4(), region_id=1)
    service.experience_tags.get_active_by_ids.return_value = [_tag(2, "역사·문화")]

    with patch(
        "app.services.place_service.kakao_api.geocode_address",
        side_effect=AppError(ErrorCode.EXTERNAL_API_UNAVAILABLE, "죽음", status_code=503),
    ):
        with pytest.raises(AppError) as exc_info:
            service.add_custom_place_to_trip(_current_user(), uuid4(), _payload())

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == ErrorCode.EXTERNAL_API_UNAVAILABLE
