"""POST /trips/{tripId}/places/custom 라우터를 dependency override 로
DB/Supabase 실접속 없이 검증한다.

Kakao 지오코딩은 "카카오맵" 제품 비활성화로 당장 못 써서, 이 라우트는 주소를
텍스트로만 저장하고 위경도는 채우지 않는다.
"""
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


def test_add_custom_place_success_returns_201(client):
    trip_id = uuid4()
    place_id = uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo, patch(
        "app.services.place_service.ExperienceTagRepository"
    ) as MockTagRepo, patch("app.services.place_service.PlaceRepository") as MockPlaceRepo, patch(
        "app.services.place_service.TripPlaceRepository"
    ) as MockTripPlaceRepo:
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
    MockPlaceRepo.return_value.create.assert_called_once_with(
        source_type="custom",
        tour_content_id=None,
        region_id=1,
        name="유성푸르지오시티",
        longitude=None,
        latitude=None,
        is_recommendable=False,
        expected_wait_minutes=60,
        address="서울 종로구 사직로 161",
    )


def test_add_custom_place_unknown_category_returns_404(client):
    trip_id = uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo, patch(
        "app.services.place_service.ExperienceTagRepository"
    ) as MockTagRepo:
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id, region_id=1)
        MockTagRepo.return_value.get_active_by_ids.return_value = []

        res = client.post(
            f"/api/trips/{trip_id}/places/custom",
            json={"name": "존재안하는곳", "categoryTagId": 999, "address": "서울 종로구"},
        )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
