"""PlaceService.add_custom_place_to_trip 을 repository mock 으로 검증한다.

Kakao 지오코딩은 "카카오맵" 제품 비활성화로 당장 못 써서, 이 플로우는 주소를
텍스트로만 저장하고 위경도는 채우지 않는다(추후 배치로 채울 예정).

경험태그(분류) 선택은 받지 않는다 — is_recommendable=False 라 추천 후보 조회에서
애초에 제외되어 저장해도 쓰이지 않았고, STEP3 완료 직후 "방문 목적" 화면에서 같은
태그 목록을 다시 물어봐서 중복 입력으로만 느껴졌다.
"""
from datetime import time
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, ErrorCode
from app.schemas.place import CustomPlaceAddRequest
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
        longitude=None,
        latitude=None,
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
