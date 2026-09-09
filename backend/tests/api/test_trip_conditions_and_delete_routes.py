"""PATCH /trips/{tripId}/conditions, DELETE /trips/{tripId} 라우터를
dependency override 로 DB/Supabase 실접속 없이 검증한다.
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


def test_patch_conditions_success_returns_data_envelope(client):
    trip_id = uuid4()
    with patch("app.services.trip_service.TripRepository") as MockTripRepo:
        fake_trip = MagicMock(
            id=trip_id, region_id=1, travel_date=None, transport_mode="walk", trip_places=[]
        )
        MockTripRepo.return_value.get_owned_by_id.return_value = fake_trip
        MockTripRepo.return_value.update_conditions.return_value = MagicMock(
            id=trip_id,
            needs_reanalysis=True,
            updated_at=datetime(2026, 8, 28, 10, 0, 0),
        )

        res = client.patch(f"/api/trips/{trip_id}/conditions", json={"transportMode": "public_transit"})

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["needsReanalysis"] is True
    assert body["data"]["warnings"] == []


def test_patch_conditions_unknown_trip_returns_404_error_envelope(client):
    with patch("app.services.trip_service.TripRepository") as MockTripRepo:
        MockTripRepo.return_value.get_owned_by_id.return_value = None

        res = client.patch(f"/api/trips/{uuid4()}/conditions", json={"transportMode": "walk"})

    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_delete_trip_success_returns_204(client):
    trip_id = uuid4()
    with patch("app.services.trip_service.TripRepository") as MockTripRepo:
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id)

        res = client.delete(f"/api/trips/{trip_id}")

    assert res.status_code == 204
    assert res.content == b""
    MockTripRepo.return_value.delete.assert_called_once()


def test_delete_trip_unknown_trip_returns_404_error_envelope(client):
    with patch("app.services.trip_service.TripRepository") as MockTripRepo:
        MockTripRepo.return_value.get_owned_by_id.return_value = None

        res = client.delete(f"/api/trips/{uuid4()}")

    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
