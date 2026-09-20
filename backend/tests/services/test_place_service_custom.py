"""PlaceService.add_custom_place_to_trip 을 repository·Kakao 지오코딩 mock 으로 검증한다.

주소는 Kakao 로컬 API로 위경도를 조회해 함께 저장한다. 조회는 DB 쓰기 전에 하므로
실패(주소 없음·서비스 장애)하면 DB 쓰기를 시작하지 않아야 한다(이후 DB 단계의 롤백은
mock 테스트로 증명하지 않는다).

경험태그(분류) 선택은 받지 않는다 — 커스텀 장소(is_recommendable=False)는 추천 후보로
뽑히지 않아 저장해도 쓰이지 않았고, STEP3 완료 직후 "방문 목적" 화면에서 같은
태그 목록을 다시 물어봐서 중복 입력으로만 느껴졌다.
"""
from datetime import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.clients.kakao_api import GeocodedAddress
from app.core.exceptions import AppError, ErrorCode
from app.schemas.place import CustomPlaceAddRequest
from app.schemas.user import CurrentUser
from app.services.place_service import PlaceService


@pytest.fixture(autouse=True)
def geocode():
    with patch("app.services.place_service.geocode_address") as mock:
        mock.return_value = GeocodedAddress(latitude=37.5759, longitude=126.9768)
        yield mock


def _service_with_mocks():
    service = PlaceService(db=MagicMock())
    service.places = MagicMock()
    service.trip_places = MagicMock()
    service.trips = MagicMock()
    service.regions = MagicMock()
    return service


def _current_user():
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")


def _payload(**overrides):
    defaults = dict(
        name="유성푸르지오시티",
        address="서울 종로구 사직로 161",
        visit_time="14:30:00",
    )
    defaults.update(overrides)
    return CustomPlaceAddRequest(**defaults)


def test_add_custom_place_success():
    service = _service_with_mocks()
    trip_id = uuid4()
    place_id = uuid4()
    trip = MagicMock(id=trip_id, region_id=1)
    service.trips.get_owned_by_id.return_value = trip
    created_place = MagicMock(id=place_id)
    created_place.name = "유성푸르지오시티"
    service.places.create.return_value = created_place
    service.trip_places.next_position.return_value = 5
    service.trip_places.add.return_value = MagicMock(
        id=uuid4(), trip_id=trip_id, position=5, is_fixed=False, visit_time=time(14, 30)
    )

    result = service.add_custom_place_to_trip(_current_user(), trip_id, _payload())

    service.places.create.assert_called_once_with(
        source_type="custom",
        tour_content_id=None,
        region_id=1,
        name="유성푸르지오시티",
        longitude=126.9768,
        latitude=37.5759,
        is_recommendable=False,
        address="서울 종로구 사직로 161",
    )
    service.trip_places.add.assert_called_once_with(
        trip_id=trip_id, place_id=place_id, position=5, visit_time=time(14, 30)
    )
    assert result.visit_order == 5
    assert result.visit_time == time(14, 30)


def test_add_custom_place_unknown_trip_returns_404():
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.add_custom_place_to_trip(_current_user(), uuid4(), _payload())

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_add_custom_place_address_outside_trip_region_returns_400():
    service = _service_with_mocks()
    trip = MagicMock(id=uuid4(), region_id=1)  # 서울특별시
    trip.region.name = "서울특별시"
    service.trips.get_owned_by_id.return_value = trip

    with pytest.raises(AppError) as exc_info:
        service.add_custom_place_to_trip(
            _current_user(), uuid4(), _payload(address="부산 해운대구 해운대해변로 264")
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == ErrorCode.ADDRESS_NOT_FOUND
    service.places.create.assert_not_called()


def test_add_custom_place_without_trip_region_skips_region_check():
    service = _service_with_mocks()
    trip_id = uuid4()
    place_id = uuid4()
    trip = MagicMock(id=trip_id, region_id=None)
    service.trips.get_owned_by_id.return_value = trip
    created_place = MagicMock(id=place_id)
    created_place.name = "유성푸르지오시티"
    service.places.create.return_value = created_place
    service.trip_places.next_position.return_value = 1
    service.trip_places.add.return_value = MagicMock(
        id=uuid4(), trip_id=trip_id, position=1, is_fixed=False, visit_time=time(14, 30)
    )

    result = service.add_custom_place_to_trip(
        _current_user(), trip_id, _payload(address="부산 해운대구 해운대해변로 264")
    )

    assert result.visit_order == 1


def _service_for_registration():
    service = _service_with_mocks()
    trip_id = uuid4()
    service.trips.get_owned_by_id.return_value = MagicMock(id=trip_id, region_id=1)
    created_place = MagicMock(id=uuid4())
    created_place.name = "유성푸르지오시티"
    service.places.create.return_value = created_place
    service.trip_places.next_position.return_value = 1
    service.trip_places.add.return_value = MagicMock(
        id=uuid4(), trip_id=trip_id, position=1, is_fixed=False, visit_time=None
    )
    return service, trip_id


def test_add_custom_place_geocodes_the_base_address_when_provided(geocode):
    service, trip_id = _service_for_registration()

    service.add_custom_place_to_trip(
        _current_user(),
        trip_id,
        _payload(address="서울 종로구 사직로 161 3층 301호", base_address="서울 종로구 사직로 161"),
    )

    geocode.assert_called_once_with("서울 종로구 사직로 161")
    assert service.places.create.call_args.kwargs["address"] == "서울 종로구 사직로 161 3층 301호"


def test_add_custom_place_geocodes_the_full_address_without_base_address(geocode):
    service, trip_id = _service_for_registration()

    service.add_custom_place_to_trip(_current_user(), trip_id, _payload())

    geocode.assert_called_once_with("서울 종로구 사직로 161")


def test_add_custom_place_stores_longitude_and_latitude_in_the_right_order(geocode):
    service, trip_id = _service_for_registration()
    geocode.return_value = GeocodedAddress(latitude=37.1, longitude=126.2)

    service.add_custom_place_to_trip(_current_user(), trip_id, _payload())

    kwargs = service.places.create.call_args.kwargs
    assert kwargs["latitude"] == 37.1
    assert kwargs["longitude"] == 126.2


def test_add_custom_place_address_not_found_returns_400_before_any_db_write(geocode):
    service, trip_id = _service_for_registration()
    geocode.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.add_custom_place_to_trip(_current_user(), trip_id, _payload())

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == ErrorCode.ADDRESS_NOT_FOUND
    service.places.create.assert_not_called()
    service.trip_places.add.assert_not_called()


def test_add_custom_place_geocoding_outage_returns_503_before_any_db_write(geocode):
    service, trip_id = _service_for_registration()
    geocode.side_effect = AppError(ErrorCode.EXTERNAL_API_UNAVAILABLE, "장애", status_code=503)

    with pytest.raises(AppError) as exc_info:
        service.add_custom_place_to_trip(_current_user(), trip_id, _payload())

    assert exc_info.value.status_code == 503
    service.places.create.assert_not_called()
    service.trip_places.add.assert_not_called()
    service.db.commit.assert_not_called()


def test_add_custom_place_outside_region_never_calls_geocoding(geocode):
    service = _service_with_mocks()
    trip = MagicMock(id=uuid4(), region_id=1)
    trip.region.name = "서울특별시"
    service.trips.get_owned_by_id.return_value = trip

    with pytest.raises(AppError):
        service.add_custom_place_to_trip(
            _current_user(), uuid4(), _payload(address="부산 해운대구 해운대해변로 264")
        )

    geocode.assert_not_called()


def test_custom_place_request_rejects_base_address_that_is_not_a_prefix_of_address():
    with pytest.raises(ValueError):
        _payload(address="서울 종로구 사직로 161 3층", base_address="서울 종로구 창경궁로 185")


def test_custom_place_request_treats_blank_base_address_as_absent():
    assert _payload(base_address="   ").base_address is None


def test_custom_place_request_rejects_base_address_that_truncates_the_street_number():
    # 두 번지 모두 실제로 존재해서, 검증이 없으면 110번지를 저장하면서 11번지 좌표를 조회한다.
    with pytest.raises(ValueError):
        _payload(address="서울 중구 세종대로 110", base_address="서울 중구 세종대로 11")


def test_custom_place_request_accepts_base_address_equal_to_address_or_followed_by_a_space():
    assert _payload(address="서울 종로구 사직로 161", base_address="서울 종로구 사직로 161").base_address
    assert _payload(
        address="서울 종로구 사직로 161 3층 301호", base_address="서울 종로구 사직로 161"
    ).base_address


def test_custom_place_request_rejects_base_address_that_is_not_a_complete_address():
    with pytest.raises(ValueError):
        _payload(address="서울 종로구 사직로 161", base_address="서울")
