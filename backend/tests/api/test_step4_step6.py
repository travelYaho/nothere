"""STEP4(집중도 분석)/STEP6(대안 후보 탐색) API 라우팅 스모크 테스트."""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.analysis.service import AnalysisService
from app.domains.recommendation.service import RecommendationService
from app.main import app
from app.schemas.user import CurrentUser


@pytest.fixture
def current_user() -> CurrentUser:
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터", profile_image_url=None)


def _override_db():
    yield MagicMock()


@pytest.fixture
def client(current_user: CurrentUser):
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_run_analysis_wraps_service_result_in_envelope(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    trip_id = uuid4()
    monkeypatch.setattr(
        AnalysisService,
        "run_analysis",
        lambda self, user, tid: {"tripId": str(tid), "highConcentrationCount": 1, "items": []},
    )
    response = client.post(f"/api/trips/{trip_id}/analysis")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["tripId"] == str(trip_id)
    assert "meta" in body


def test_get_analysis_passes_status_query_through(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    trip_id = uuid4()
    captured = {}

    def _fake_get_analysis(self, user, tid, status_filter):
        captured["status_filter"] = status_filter
        return {"tripId": str(tid), "highConcentrationCount": 0, "items": []}

    monkeypatch.setattr(AnalysisService, "get_analysis", _fake_get_analysis)
    response = client.get(f"/api/trips/{trip_id}/analysis", params={"status": "CROWDED"})
    assert response.status_code == 200
    assert captured["status_filter"] == "CROWDED"


def test_create_recommendation_request_delegates_to_service(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    trip_place_id = uuid4()
    request_id = uuid4()
    captured = {}

    def _fake_create_request(self, tp_id, user, purpose_tag_ids, search_mode):
        captured["purpose_tag_ids"] = purpose_tag_ids
        captured["search_mode"] = search_mode
        return {
            "requestId": str(request_id),
            "tripPlaceId": str(tp_id),
            "searchMode": search_mode or "default",
            "status": "success",
            "candidateCount": 2,
            "excludedCount": 0,
        }

    monkeypatch.setattr(RecommendationService, "create_request", _fake_create_request)
    response = client.post(
        f"/api/trip-places/{trip_place_id}/recommendation-requests",
        json={"purposeTagIds": [1, 2], "searchMode": "default"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["requestId"] == str(request_id)
    assert body["data"]["candidateCount"] == 2
    assert captured["purpose_tag_ids"] == [1, 2]
    assert captured["search_mode"] == "default"


def test_create_recommendation_request_without_body(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    trip_place_id = uuid4()
    monkeypatch.setattr(
        RecommendationService,
        "create_request",
        lambda self, tp_id, user, purpose_tag_ids, search_mode: {
            "requestId": str(uuid4()),
            "tripPlaceId": str(tp_id),
            "searchMode": "default",
            "status": "no_candidate",
            "candidateCount": 0,
            "excludedCount": 0,
        },
    )
    response = client.post(f"/api/trip-places/{trip_place_id}/recommendation-requests")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "no_candidate"


def test_list_experience_tags_is_public(client: TestClient):
    app.dependency_overrides.pop(get_current_user, None)
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    response = client.get("/api/experience-tags")
    assert response.status_code == 200
    assert response.json()["data"] == []
