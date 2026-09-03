"""GET/PUT /trip-places/{tripPlaceId}/purpose 라우터를 dependency override 로
DB/Supabase 실접속 없이 검증한다.
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.db.session import get_db
from app.main import app
from app.schemas.user import CurrentUser


def _tag(tag_id, name):
    t = MagicMock(id=tag_id)
    t.name = name
    return t


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


def test_get_purpose_returns_data_envelope(client):
    trip_place_id = uuid4()
    with patch("app.services.purpose_service.TripPlaceRepository") as MockTripPlaceRepo, patch(
        "app.services.purpose_service.TripPlacePurposeRepository"
    ) as MockPurposeRepo, patch("app.services.purpose_service.ExperienceTagRepository") as MockTagRepo:
        MockTripPlaceRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_place_id)
        MockPurposeRepo.return_value.list_by_trip_place.return_value = [MagicMock(purpose_tag_id=6)]
        MockTagRepo.return_value.get_by_ids.return_value = [_tag(6, "카페·휴식")]

        res = client.get(f"/api/trip-places/{trip_place_id}/purpose")

    assert res.status_code == 200
    body = res.json()
    assert body["data"]["purposeTags"] == [{"id": 6, "name": "카페·휴식"}]


def test_put_purpose_replaces_previous_selection(client):
    """완료 기준: PUT 재호출 시 이전 선택이 정확히 교체된다.

    실제 DB로 왕복시킬 순 없으니, TripPlacePurposeRepository.replace_all 이
    "삭제 후 재삽입" 방식으로 호출되는지 — 즉 두 번째 PUT이 첫 번째 선택을
    남겨두지 않고 새 값으로 완전히 덮어쓰는지를 라우터 레벨에서 확인한다.
    """
    trip_place_id = uuid4()
    with patch("app.services.purpose_service.TripPlaceRepository") as MockTripPlaceRepo, patch(
        "app.services.purpose_service.TripPlacePurposeRepository"
    ) as MockPurposeRepo, patch("app.services.purpose_service.ExperienceTagRepository") as MockTagRepo:
        MockTripPlaceRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_place_id)
        MockTagRepo.return_value.get_active_by_ids.side_effect = lambda ids: [MagicMock(id=i) for i in ids]
        MockTagRepo.return_value.get_by_ids.side_effect = lambda ids: [_tag(i, f"tag{i}") for i in ids]

        res1 = client.put(f"/api/trip-places/{trip_place_id}/purpose", json={"purposeTagIds": [6, 1]})
        assert res1.status_code == 200
        assert [t["id"] for t in res1.json()["data"]["purposeTags"]] == [6, 1]

        res2 = client.put(f"/api/trip-places/{trip_place_id}/purpose", json={"purposeTagIds": [3]})
        assert res2.status_code == 200
        assert [t["id"] for t in res2.json()["data"]["purposeTags"]] == [3]

    # 매 PUT 마다 전체 교체(delete-all + insert-all) 방식으로 호출됐는지 확인
    assert MockPurposeRepo.return_value.replace_all.call_args_list == [
        ((trip_place_id, [6, 1]),),
        ((trip_place_id, [3]),),
    ]


def test_put_purpose_with_empty_array_clears_selection(client):
    trip_place_id = uuid4()
    with patch("app.services.purpose_service.TripPlaceRepository") as MockTripPlaceRepo, patch(
        "app.services.purpose_service.TripPlacePurposeRepository"
    ) as MockPurposeRepo:
        MockTripPlaceRepo.return_value.get_owned_by_id.return_value = MagicMock(id=trip_place_id)

        res = client.put(f"/api/trip-places/{trip_place_id}/purpose", json={"purposeTagIds": []})

    assert res.status_code == 200
    assert res.json()["data"]["purposeTags"] == []
    MockPurposeRepo.return_value.replace_all.assert_called_once_with(trip_place_id, [])


def test_get_purpose_unknown_trip_place_returns_404_error_envelope(client):
    with patch("app.services.purpose_service.TripPlaceRepository") as MockTripPlaceRepo:
        MockTripPlaceRepo.return_value.get_owned_by_id.return_value = None

        res = client.get(f"/api/trip-places/{uuid4()}/purpose")

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
