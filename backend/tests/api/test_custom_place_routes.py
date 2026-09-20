"""POST /trips/{tripId}/places/custom 라우터를 dependency override 로
DB/Supabase 실접속 없이 검증한다.

주소의 위경도는 Kakao 지오코딩(geocode_address)으로 조회해 저장한다 — 테스트에서는
이 함수만 mock 으로 대체해 외부 호출 없이 라우트 전체 흐름을 검증한다.
"""
from datetime import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.clients.kakao_api import GeocodedAddress
from app.core.exceptions import AppError, ErrorCode
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
        "app.services.place_service.PlaceRepository"
    ) as MockPlaceRepo, patch(
        "app.services.place_service.TripPlaceRepository"
    ) as MockTripPlaceRepo, patch(
        "app.services.place_service.geocode_address",
        return_value=GeocodedAddress(latitude=37.5759, longitude=126.9768),
    ) as mock_geocode:
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id, region_id=1)
        created_place = MagicMock(id=place_id)
        created_place.name = "유성푸르지오시티"
        MockPlaceRepo.return_value.create.return_value = created_place
        MockTripPlaceRepo.return_value.next_position.return_value = 1
        MockTripPlaceRepo.return_value.add.return_value = MagicMock(
            id=uuid4(), trip_id=trip_id, position=1, is_fixed=False, visit_time=time(14, 30)
        )

        res = client.post(
            f"/api/trips/{trip_id}/places/custom",
            json={
                "name": "유성푸르지오시티",
                "address": "서울 종로구 사직로 161 3층",
                "baseAddress": "서울 종로구 사직로 161",
                "visitTime": "14:30:00",
            },
        )

    assert res.status_code == 201
    body = res.json()
    assert body["data"]["name"] == "유성푸르지오시티"
    assert body["data"]["visitOrder"] == 1
    assert body["data"]["visitTime"] == "14:30:00"
    MockPlaceRepo.return_value.create.assert_called_once_with(
        source_type="custom",
        tour_content_id=None,
        region_id=1,
        name="유성푸르지오시티",
        longitude=126.9768,
        latitude=37.5759,
        is_recommendable=False,
        address="서울 종로구 사직로 161 3층",
    )
    mock_geocode.assert_called_once_with("서울 종로구 사직로 161")
    MockTripPlaceRepo.return_value.add.assert_called_once_with(
        trip_id=trip_id, place_id=place_id, position=1, visit_time=time(14, 30)
    )


def test_add_custom_place_unknown_trip_returns_404(client):
    trip_id = uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo:
        MockTripRepo.return_value.get_owned_by_id.return_value = None

        res = client.post(
            f"/api/trips/{trip_id}/places/custom",
            json={"name": "존재안하는곳", "address": "서울 종로구 사직로 161"},
        )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_add_custom_place_incomplete_address_returns_422(client):
    trip_id = uuid4()

    res = client.post(
        f"/api/trips/{trip_id}/places/custom",
        json={"name": "존재안하는곳", "address": "서울시"},
    )

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_add_custom_place_geocoding_outage_returns_503_before_any_db_write(client):
    trip_id = uuid4()
    with patch("app.services.place_service.TripRepository") as MockTripRepo, patch(
        "app.services.place_service.PlaceRepository"
    ) as MockPlaceRepo, patch("app.services.place_service.TripPlaceRepository") as MockTripPlaceRepo, patch(
        "app.services.place_service.geocode_address",
        side_effect=AppError(ErrorCode.EXTERNAL_API_UNAVAILABLE, "장애", status_code=503),
    ):
        MockTripRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_id, region_id=1)

        res = client.post(
            f"/api/trips/{trip_id}/places/custom",
            json={"name": "유성푸르지오시티", "address": "서울 종로구 사직로 161"},
        )

    assert res.status_code == 503
    assert res.json()["error"]["code"] == "EXTERNAL_API_UNAVAILABLE"
    MockPlaceRepo.return_value.create.assert_not_called()
    MockTripPlaceRepo.return_value.add.assert_not_called()


def test_add_custom_place_base_address_not_prefix_of_address_returns_422(client):
    res = client.post(
        f"/api/trips/{uuid4()}/places/custom",
        json={
            "name": "유성푸르지오시티",
            "address": "서울 종로구 사직로 161 3층",
            "baseAddress": "서울 종로구 창경궁로 185",
        },
    )

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_add_custom_place_truncated_base_address_returns_422(client):
    res = client.post(
        f"/api/trips/{uuid4()}/places/custom",
        json={
            "name": "세종대로",
            "address": "서울 중구 세종대로 110",
            "baseAddress": "서울 중구 세종대로 11",
        },
    )

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
