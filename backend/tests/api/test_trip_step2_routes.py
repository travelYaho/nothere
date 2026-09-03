"""GET /regions, GET /experience-tags, POST /trips 라우터를 dependency override 로
DB/Supabase 실접속 없이 검증한다.
"""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.db.session import get_db
from app.main import app
from app.schemas.user import CurrentUser

TOMORROW = (date.today() + timedelta(days=1)).isoformat()


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


def test_list_regions_returns_data_envelope(client):
    fake_region = MagicMock(id=1)
    fake_region.name = "서울특별시"  # MagicMock(name=...)는 mock 자체의 repr용 이름이라 별도로 설정해야 한다.
    with patch("app.api.v1.regions.RegionRepository") as MockRepo:
        MockRepo.return_value.list_supported.return_value = [fake_region]
        res = client.get("/api/regions")

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["regions"] == [{"id": 1, "name": "서울특별시"}]


def test_list_experience_tags_returns_data_envelope(client):
    fake_tag = MagicMock(id=6)
    fake_tag.name = "카페·휴식"
    with patch("app.api.v1.experience_tags.ExperienceTagRepository") as MockRepo:
        MockRepo.return_value.list_active.return_value = [fake_tag]
        res = client.get("/api/experience-tags")

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["experienceTags"] == [{"id": 6, "name": "카페·휴식"}]


def test_create_trip_success_returns_201_with_data_envelope(client):
    with patch("app.services.trip_service.RegionRepository") as MockRegionRepo, patch(
        "app.services.trip_service.ExperienceTagRepository"
    ) as MockTagRepo, patch("app.services.trip_service.TripRepository") as MockTripRepo:
        MockRegionRepo.return_value.get_supported_by_id.return_value = MagicMock(id=12)
        MockTagRepo.return_value.get_active_by_ids.return_value = [6, 1, 3]
        MockTripRepo.return_value.create_trip.return_value = MagicMock(
            id=uuid4(),
            title="2026.09.12 가족 여행",
            status="draft",
            current_step=3,
            created_at="2026-08-28T10:00:00Z",
        )

        res = client.post(
            "/api/trips",
            json={
                "title": None,
                "travelDate": "2026-09-12",
                "regionId": 12,
                "companionType": "family",
                "transportMode": "public_transit",
                "extraTimeLimitMinutes": None,
                "preferredExperienceTagIds": [6, 1, 3],
            },
        )

    assert res.status_code == 201
    body = res.json()
    assert body["data"]["title"] == "2026.09.12 가족 여행"
    assert body["data"]["status"] == "draft"
    assert body["data"]["currentStep"] == 3


def test_create_trip_invalid_count_returns_400_error_envelope(client):
    res = client.post(
        "/api/trips",
        json={
            "travelDate": TOMORROW,
            "regionId": 12,
            "preferredExperienceTagIds": [1],
        },
    )

    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "INVALID_PREFERRED_EXPERIENCE_COUNT"


def test_create_trip_missing_required_field_returns_422(client):
    res = client.post("/api/trips", json={"regionId": 12, "preferredExperienceTagIds": [1, 2]})

    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
