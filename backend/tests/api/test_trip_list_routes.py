"""GET /trips(목록) 라우터를 dependency override 로 DB/Supabase 실접속 없이 검증한다."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

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


def _fake_trip_row(status="draft"):
    trip = MagicMock()
    trip.id = uuid4()
    trip.title = "제주도 여행"
    trip.travel_date = None
    trip.status = status
    trip.region.name = "제주"
    return trip


def test_list_trips_returns_mapped_trips(client):
    with patch("app.services.trip_service.TripRepository") as MockTripRepo, patch(
        "app.services.trip_service.TripPlaceRepository"
    ) as MockTripPlaceRepo:
        trip = _fake_trip_row("confirmed")
        MockTripRepo.return_value.list_by_user.return_value = ([trip], 1)
        MockTripPlaceRepo.return_value.count_by_trip.return_value = 3

        res = client.get("/api/trips")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["page"] == 1
    assert body["totalCount"] == 1
    assert body["trips"][0]["tripId"] == str(trip.id)
    assert body["trips"][0]["placeCount"] == 3
    assert body["trips"][0]["resumeUrl"] == f"/trips/{trip.id}/guide"


def test_list_trips_forwards_status_filter_and_page(client):
    with patch("app.services.trip_service.TripRepository") as MockTripRepo, patch(
        "app.services.trip_service.TripPlaceRepository"
    ):
        MockTripRepo.return_value.list_by_user.return_value = ([], 0)

        client.get("/api/trips?status=draft&page=2")

        MockTripRepo.return_value.list_by_user.assert_called_once()
        _, kwargs = MockTripRepo.return_value.list_by_user.call_args
        assert kwargs["status_filter"] == "draft"
        assert kwargs["page"] == 2


def test_list_trips_rejects_invalid_status(client):
    res = client.get("/api/trips?status=bogus")

    assert res.status_code == 422
