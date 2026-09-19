"""app.services.trip_summary 의 순수 변환 로직을 검증한다."""
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.trip_summary import build_schedule_summary, build_trip_summary, resume_path


def _fake_trip(status: str):
    trip = MagicMock()
    trip.id = uuid4()
    trip.title = "제주도 여행"
    trip.travel_date = None
    trip.status = status
    trip.region.name = "제주"
    return trip


def test_resume_path_confirmed_goes_to_saved():
    trip = _fake_trip("confirmed")
    assert resume_path(trip) == f"/trips/{trip.id}/saved"


def test_resume_path_completed_goes_to_saved():
    trip = _fake_trip("completed")
    assert resume_path(trip) == f"/trips/{trip.id}/saved"


def test_resume_path_draft_goes_to_places():
    trip = _fake_trip("draft")
    assert resume_path(trip) == f"/trips/{trip.id}/places"


def test_build_schedule_summary_uses_schedule_id_field():
    trip = _fake_trip("draft")

    summary = build_schedule_summary(trip, 3)

    assert summary.schedule_id == trip.id
    assert summary.place_count == 3
    assert summary.region_name == "제주"
    assert summary.resume_url == f"/trips/{trip.id}/places"


def test_build_trip_summary_uses_trip_id_field():
    trip = _fake_trip("confirmed")

    summary = build_trip_summary(trip, 5)

    assert summary.trip_id == trip.id
    assert summary.place_count == 5
    assert summary.resume_url == f"/trips/{trip.id}/saved"
