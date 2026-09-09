"""RecommendationService.create_request(STEP6) 동작 검증."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, ErrorCode
from app.domains.recommendation import candidates as candidate_pipeline
from app.domains.recommendation.service import RecommendationService
from app.schemas.user import CurrentUser


def _user() -> CurrentUser:
    return CurrentUser(id=uuid4(), email="t@example.com", nickname="테스터", profile_image_url=None)


def _setup_common(svc: RecommendationService, user: CurrentUser, monkeypatch):
    trip_place_id = uuid4()
    trip_id = uuid4()
    place_id = uuid4()

    tp = SimpleNamespace(id=trip_place_id, trip_id=trip_id, place_id=place_id)
    trip = SimpleNamespace(id=trip_id, user_id=user.id, travel_date=None)

    svc.repo.get_trip_place = MagicMock(return_value=tp)
    svc.repo.get_trip_owned = MagicMock(return_value=trip)
    svc.repo.get_experience_tag_code_map = MagicMock(return_value={"history_culture": 1})
    svc.repo.list_trip_place_ids = MagicMock(return_value={place_id})
    svc.repo.get_places_map = MagicMock(return_value={place_id: SimpleNamespace(name="원래장소")})
    svc.repo.list_nearby_recommendable_places = MagicMock(return_value=[])

    monkeypatch.setattr(
        "app.domains.recommendation.service.get_place_coords",
        lambda db, place_id: (37.5, 127.0),
    )
    return trip_place_id


def test_create_request_rejects_invalid_search_mode():
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    svc.repo.get_trip_place = MagicMock(return_value=SimpleNamespace(id=uuid4(), trip_id=uuid4(), place_id=uuid4()))
    svc.repo.get_trip_owned = MagicMock(return_value=SimpleNamespace(id=uuid4(), user_id=user.id))

    with pytest.raises(AppError) as exc:
        svc.create_request(uuid4(), user, purpose_tag_ids=None, search_mode="not_a_mode")

    assert exc.value.code == ErrorCode.INVALID_SEARCH_MODE


def test_create_request_raises_when_origin_has_no_coords(monkeypatch):
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    svc.repo.get_trip_place = MagicMock(return_value=SimpleNamespace(id=uuid4(), trip_id=uuid4(), place_id=uuid4()))
    svc.repo.get_trip_owned = MagicMock(return_value=SimpleNamespace(id=uuid4(), user_id=user.id))
    monkeypatch.setattr(
        "app.domains.recommendation.service.get_place_coords", lambda db, place_id: None
    )

    with pytest.raises(AppError) as exc:
        svc.create_request(uuid4(), user, purpose_tag_ids=None, search_mode=None)

    assert exc.value.status_code == 422


def test_create_request_creates_candidates_from_tour_api(monkeypatch):
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_place_id = _setup_common(svc, user, monkeypatch)

    tour_item = SimpleNamespace(
        content_id="tour-1",
        name="창덕궁",
        latitude=37.58,
        longitude=127.0,
        area_cd="11",
        signgu_cd="11110",
        category_code="A0201",
    )
    monkeypatch.setattr(candidate_pipeline, "fetch_nearby_places", lambda *a, **k: [tour_item])
    monkeypatch.setattr(
        candidate_pipeline, "get_spots_and_items_for_codes", lambda *a, **k: ([], {}, False)
    )

    created_place = SimpleNamespace(id=uuid4())
    svc.repo.get_or_create_place_by_tour_content_id = MagicMock(return_value=created_place)
    svc.repo.upsert_place_experience_tags = MagicMock()

    saved_request = SimpleNamespace(id=uuid4())
    svc.repo.create_request_with_candidates = MagicMock(return_value=saved_request)

    result = svc.create_request(
        trip_place_id, user, purpose_tag_ids=[1], search_mode="default"
    )

    assert result["status"] == "success"
    assert result["candidateCount"] == 1
    svc.repo.create_request_with_candidates.assert_called_once()
    args, _ = svc.repo.create_request_with_candidates.call_args
    row_dicts = args[3]
    assert row_dicts[0]["candidate_place_id"] == created_place.id
    assert row_dicts[0]["feasibility_status"] == "UNKNOWN"
    assert isinstance(row_dicts[0]["experience_score"], Decimal)


def test_create_request_no_candidate_status_when_all_filtered(monkeypatch):
    db = MagicMock()
    svc = RecommendationService(db)
    user = _user()
    trip_place_id = _setup_common(svc, user, monkeypatch)

    monkeypatch.setattr(candidate_pipeline, "fetch_nearby_places", lambda *a, **k: [])
    saved_request = SimpleNamespace(id=uuid4())
    svc.repo.create_request_with_candidates = MagicMock(return_value=saved_request)

    result = svc.create_request(trip_place_id, user, purpose_tag_ids=None, search_mode="default")

    assert result["status"] == "no_candidate"
    assert result["candidateCount"] == 0
