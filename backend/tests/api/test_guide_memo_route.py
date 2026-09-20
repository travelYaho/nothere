"""가이드북 메모 PATCH 라우터."""
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


def test_patch_guide_memo_returns_saved_text(client):
    trip_id = uuid4()
    with patch("app.api.trips.RecommendationService") as MockService:
        MockService.return_value.update_guide_memo.return_value = {"memo": "여행 메모"}
        res = client.patch(f"/api/trips/{trip_id}/guide/memo", json={"content": "여행 메모"})

    assert res.status_code == 200
    assert res.json()["data"]["memo"] == "여행 메모"
    MockService.return_value.update_guide_memo.assert_called_once()
