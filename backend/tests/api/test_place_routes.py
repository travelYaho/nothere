"""GET /places/search, POST /trips/{tripId}/places 라우터를 dependency override 로
DB/Supabase/TourAPI 실접속 없이 검증한다.
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.clients.tour_api import TourApiPlace
from app.core.security import get_current_user
from app.db.session import get_db
from app.main import app
from app.schemas.user import CurrentUser


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _auth_override():
    fake_user = CurrentUser(
        id=uuid4(), email="tester@example.com", nickname="테스터", profile_image_url=None
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield
    app.dependency_overrides.clear()


def test_search_places_returns_data_envelope(client):
    with patch("app.services.place_service.tour_api.search_places") as mock_search, patch(
        "app.services.place_service.PlaceRepository"
    ) as MockPlaceRepo:
        mock_search.return_value = [
            TourApiPlace(content_id="126508", name="경복궁", category="역사·문화",
                         address="서울 종로구", latitude=37.579617, longitude=126.977041)
        ]
        MockPlaceRepo.return_value.get_by_source.return_value = None
        MockPlaceRepo.return_value.create.return_value = MagicMock(id=uuid4())

        res = client.get("/api/places/search", params={"keyword": "경복궁", "regionId": 1})

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["places"][0]["name"] == "경복궁"
    assert body["data"]["places"][0]["latitude"] == pytest.approx(37.579617)


def test_search_places_external_api_unavailable_returns_503_error_envelope(client):
    with patch("app.services.place_service.tour_api.settings") as mock_settings:
        mock_settings.TOUR_API_KEY = ""
        res = client.get("/api/places/search", params={"keyword": "경복궁"})

    assert res.status_code == 503
    body = res.json()
    assert body["error"]["code"] == "EXTERNAL_API_UNAVAILABLE"


def test_add_trip_place_success_returns_201(client):
    trip_id = uuid4()
    place_id = uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo, patch(
        "app.services.place_service.PlaceRepository"
    ) as MockPlaceRepo, patch("app.services.place_service.TripPlaceRepository") as MockTripPlaceRepo:
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id)
        MockPlaceRepo.return_value.get_by_id.return_value = MagicMock(id=place_id)
        MockTripPlaceRepo.return_value.exists.return_value = False
        MockTripPlaceRepo.return_value.next_position.return_value = 1
        MockTripPlaceRepo.return_value.add.return_value = MagicMock(
            id=uuid4(), trip_id=trip_id, place_id=place_id, position=1, is_fixed=False
        )

        res = client.post(f"/api/trips/{trip_id}/places", json={"placeId": str(place_id)})

    assert res.status_code == 201
    body = res.json()
    assert body["data"]["visitOrder"] == 1
    assert body["data"]["isFixed"] is False


def test_add_trip_place_duplicate_returns_409_error_envelope(client):
    trip_id = uuid4()
    place_id = uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo, patch(
        "app.services.place_service.PlaceRepository"
    ) as MockPlaceRepo, patch("app.services.place_service.TripPlaceRepository") as MockTripPlaceRepo:
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id)
        MockPlaceRepo.return_value.get_by_id.return_value = MagicMock(id=place_id)
        MockTripPlaceRepo.return_value.exists.return_value = True

        res = client.post(f"/api/trips/{trip_id}/places", json={"placeId": str(place_id)})

    assert res.status_code == 409
    body = res.json()
    assert body["error"]["code"] == "DUPLICATE_PLACE_ID"
