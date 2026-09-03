"""DELETE /trip-places/{id}, PATCH /trips/{id}/places/order, PATCH /trip-places/{id}
라우터를 dependency override 로 DB/Supabase 실접속 없이 검증한다.
"""
from datetime import datetime
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


def test_delete_trip_place_success_returns_204(client):
    trip_place_id = uuid4()
    with patch("app.services.place_service.TripPlaceRepository") as MockRepo:
        MockRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_place_id, trip_id=uuid4())
        MockRepo.return_value.count_by_trip.return_value = 3

        res = client.delete(f"/api/trip-places/{trip_place_id}")

    assert res.status_code == 204
    assert res.content == b""


def test_delete_last_trip_place_returns_409_with_remaining_count(client):
    trip_place_id = uuid4()
    with patch("app.services.place_service.TripPlaceRepository") as MockRepo:
        MockRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_place_id, trip_id=uuid4())
        MockRepo.return_value.count_by_trip.return_value = 1

        res = client.delete(f"/api/trip-places/{trip_place_id}")

    assert res.status_code == 409
    body = res.json()
    assert body["error"]["code"] == "MINIMUM_PLACES_REQUIRED"
    assert body["error"]["remainingCount"] == 0


def test_reorder_places_success_returns_data_envelope(client):
    trip_id = uuid4()
    tp1, tp2 = uuid4(), uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo, patch(
        "app.services.place_service.TripPlaceRepository"
    ) as MockTripPlaceRepo:
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id)
        MockTripPlaceRepo.return_value.get_owned_by_ids.return_value = [MagicMock(), MagicMock()]
        MockTripRepo.return_value.mark_needs_reanalysis.return_value = MagicMock(
            id=trip_id, needs_reanalysis=True, updated_at=datetime(2026, 1, 1)
        )

        res = client.patch(
            f"/api/trips/{trip_id}/places/order",
            json={"order": [
                {"tripPlaceId": str(tp1), "visitOrder": 1},
                {"tripPlaceId": str(tp2), "visitOrder": 2},
            ]},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["needsReanalysis"] is True


def test_update_trip_place_visit_success_returns_data_envelope(client):
    trip_place_id = uuid4()
    with patch("app.services.place_service.TripPlaceRepository") as MockRepo:
        MockRepo.return_value.get_owned_by_id.return_value = MagicMock()
        MockRepo.return_value.update_visit.return_value = MagicMock(
            id=trip_place_id,
            visit_time=None,
            stay_minutes=60,
            is_fixed=True,
            updated_at=datetime(2026, 1, 1),
            trip=MagicMock(needs_reanalysis=False),
        )

        res = client.patch(
            f"/api/trip-places/{trip_place_id}",
            json={"visitTime": "10:00", "durationMinutes": 60, "isFixed": True},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["durationMinutes"] == 60
    assert body["data"]["isFixed"] is True
    assert body["data"]["needsReanalysis"] is False
