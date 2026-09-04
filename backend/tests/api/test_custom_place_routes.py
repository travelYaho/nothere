"""POST /trips/{tripId}/places/custom 라우터를 dependency override 로
DB/Supabase/Kakao 실접속 없이 검증한다.
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.clients.kakao_api import GeocodedAddress
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


def test_add_custom_place_success_returns_201(client):
    trip_id = uuid4()
    place_id = uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo, patch(
        "app.services.place_service.ExperienceTagRepository"
    ) as MockTagRepo, patch("app.services.place_service.PlaceRepository") as MockPlaceRepo, patch(
        "app.services.place_service.TripPlaceRepository"
    ) as MockTripPlaceRepo, patch(
        "app.services.place_service.kakao_api.geocode_address",
        return_value=GeocodedAddress(latitude=37.57, longitude=126.97),
    ):
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id, region_id=1)
        tag = MagicMock(id=2)
        tag.name = "역사·문화"
        MockTagRepo.return_value.get_active_by_ids.return_value = [tag]
        created_place = MagicMock(id=place_id)
        created_place.name = "유성푸르지오시티"
        MockPlaceRepo.return_value.create.return_value = created_place
        MockTripPlaceRepo.return_value.next_position.return_value = 1
        MockTripPlaceRepo.return_value.add.return_value = MagicMock(
            id=uuid4(), trip_id=trip_id, position=1, is_fixed=False
        )

        res = client.post(
            f"/api/trips/{trip_id}/places/custom",
            json={
                "name": "유성푸르지오시티",
                "categoryTagId": 2,
                "address": "서울 종로구 사직로 161",
                "expectedWaitMinutes": 60,
            },
        )

    assert res.status_code == 201
    body = res.json()
    assert body["data"]["name"] == "유성푸르지오시티"
    assert body["data"]["category"] == "역사·문화"
    assert body["data"]["visitOrder"] == 1


def test_add_custom_place_address_not_found_returns_400(client):
    trip_id = uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo, patch(
        "app.services.place_service.ExperienceTagRepository"
    ) as MockTagRepo, patch(
        "app.services.place_service.kakao_api.geocode_address", return_value=None
    ):
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id, region_id=1)
        tag = MagicMock(id=2)
        tag.name = "역사·문화"
        MockTagRepo.return_value.get_active_by_ids.return_value = [tag]

        res = client.post(
            f"/api/trips/{trip_id}/places/custom",
            json={
                "name": "존재안하는곳",
                "categoryTagId": 2,
                "address": "asdkjaslkdjas",
            },
        )

    assert res.status_code == 400
    assert res.json()["error"]["code"] == "ADDRESS_NOT_FOUND"


def test_add_custom_place_kakao_unavailable_returns_503(client):
    trip_id = uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo, patch(
        "app.services.place_service.ExperienceTagRepository"
    ) as MockTagRepo, patch("app.services.place_service.kakao_api.settings") as mock_settings:
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id, region_id=1)
        tag = MagicMock(id=2)
        tag.name = "역사·문화"
        MockTagRepo.return_value.get_active_by_ids.return_value = [tag]
        mock_settings.KAKAO_REST_API_KEY = ""

        res = client.post(
            f"/api/trips/{trip_id}/places/custom",
            json={"name": "유성푸르지오시티", "categoryTagId": 2, "address": "서울 종로구"},
        )

    assert res.status_code == 503
    assert res.json()["error"]["code"] == "EXTERNAL_API_UNAVAILABLE"
