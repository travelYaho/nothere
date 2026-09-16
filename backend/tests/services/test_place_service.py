"""PlaceService.search_places / add_place_to_trip 을 repository/TourAPI mock 으로 검증한다."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.clients.tour_api import TourApiPlace
from app.core.exceptions import AppError, ErrorCode
from app.schemas.place import TripPlaceAddRequest
from app.schemas.user import CurrentUser
from app.services.place_service import PlaceService


def _service_with_mocks():
    service = PlaceService(db=MagicMock())
    service.places = MagicMock()
    service.trip_places = MagicMock()
    service.trips = MagicMock()
    service.regions = MagicMock()
    service.regions.get_supported_by_id.return_value = MagicMock(id=1)
    return service


def _current_user():
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")


# --- search_places ---

def test_search_places_creates_new_place_when_not_seen_before():
    """get_or_create()가 새 place를 만들어 돌려주는 경로 — 신규/재사용 판단 자체는 이제
    PlaceRepository.get_or_create() 내부(원자적 ON CONFLICT) 책임이라 여기서는 서비스가
    그 결과를 그대로 응답에 반영하는지만 확인한다(내부 분기는 test_place_repository.py)."""
    service = _service_with_mocks()
    new_place = MagicMock(id=uuid4(), area_cd="11", signgu_cd="11110")
    service.places.get_or_create.return_value = new_place

    tour_result = TourApiPlace(
        content_id="126508", name="경복궁",
        address="서울 종로구", latitude=37.579617, longitude=126.977041,
        area_cd="11", signgu_cd="11110",
    )
    with patch("app.services.place_service.tour_api.search_places", return_value=[tour_result]):
        result = service.search_places("경복궁", region_id=1)

    assert len(result.places) == 1
    assert result.places[0].place_id == new_place.id
    assert result.places[0].name == "경복궁"
    service.places.get_or_create.assert_called_once()
    service.db.commit.assert_called_once()


def test_search_places_reuses_existing_place_for_same_content_id():
    service = _service_with_mocks()
    existing_place = MagicMock(id=uuid4(), area_cd="11", signgu_cd="11110")
    service.places.get_or_create.return_value = existing_place

    tour_result = TourApiPlace(content_id="126508", name="경복궁")
    with patch("app.services.place_service.tour_api.search_places", return_value=[tour_result]):
        result = service.search_places("경복궁", region_id=None)

    assert result.places[0].place_id == existing_place.id


def test_search_places_maps_region_id_to_tour_api_area_code():
    service = _service_with_mocks()
    service.places.get_by_source.return_value = MagicMock(id=uuid4())

    with patch("app.services.place_service.tour_api.search_places", return_value=[]) as mock_search:
        service.search_places("궁", region_id=2)  # 부산광역시

    mock_search.assert_called_once_with("궁", area_code="6")


def test_search_places_unknown_region_returns_404():
    service = _service_with_mocks()
    service.regions.get_supported_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.search_places("궁", region_id=999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_search_places_without_region_id_skips_area_code():
    service = _service_with_mocks()

    with patch("app.services.place_service.tour_api.search_places", return_value=[]) as mock_search:
        service.search_places("궁", region_id=None)

    mock_search.assert_called_once_with("궁", area_code=None)
    service.regions.get_supported_by_id.assert_not_called()


# --- add_place_to_trip ---

def test_add_place_to_trip_success():
    service = _service_with_mocks()
    trip_id = uuid4()
    place_id = uuid4()
    service.trips.get_owned_by_id.return_value = MagicMock(id=trip_id)
    service.places.get_by_id.return_value = MagicMock(id=place_id)
    service.trip_places.exists.return_value = False
    service.trip_places.next_position.return_value = 3
    service.trip_places.add.return_value = MagicMock(
        id=uuid4(), trip_id=trip_id, place_id=place_id, position=3, visit_time=None, is_fixed=False
    )

    result = service.add_place_to_trip(_current_user(), trip_id, TripPlaceAddRequest(place_id=place_id))

    assert result.visit_order == 3
    assert result.is_fixed is False
    service.trip_places.add.assert_called_once_with(
        trip_id=trip_id, place_id=place_id, position=3, visit_time=None
    )


def test_add_place_to_trip_unknown_trip_returns_404():
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.add_place_to_trip(_current_user(), uuid4(), TripPlaceAddRequest(place_id=uuid4()))

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_add_place_to_trip_unknown_place_returns_404():
    service = _service_with_mocks()
    service.trips.get_owned_by_id.return_value = MagicMock(id=uuid4())
    service.places.get_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.add_place_to_trip(_current_user(), uuid4(), TripPlaceAddRequest(place_id=uuid4()))

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_add_place_to_trip_duplicate_returns_409():
    service = _service_with_mocks()
    trip_id = uuid4()
    place_id = uuid4()
    service.trips.get_owned_by_id.return_value = MagicMock(id=trip_id)
    service.places.get_by_id.return_value = MagicMock(id=place_id)
    service.trip_places.exists.return_value = True

    with pytest.raises(AppError) as exc_info:
        service.add_place_to_trip(_current_user(), trip_id, TripPlaceAddRequest(place_id=place_id))

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == ErrorCode.DUPLICATE_PLACE_ID
    service.trip_places.add.assert_not_called()
