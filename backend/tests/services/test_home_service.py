"""HomeService 가 Schedule -> Trip 전환 후에도 기존 응답 계약을 지키는지 검증한다.

실제 DB 없이, TripRepository 를 가짜 객체로 바꿔서 순수 조합 로직만 확인한다.
"""
from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

from app.schemas.user import CurrentUser
from app.services.home_service import HomeService


def _fake_trip(**overrides):
    trip = MagicMock()
    trip.id = overrides.get("id", uuid4())
    trip.title = overrides.get("title", "제주도 여행")
    trip.travel_date = overrides.get("travel_date", date(2026, 9, 12))
    trip.status = overrides.get("status", "draft")
    trip.region.name = overrides.get("region_name", "제주")
    return trip


def test_get_home_maps_trip_fields_into_legacy_schedule_summary_shape():
    """Trip 객체를 ScheduleSummary(schedule_id/title/travel_date/status) 로 정확히 옮기는지 확인.

    HomeResponse 의 draft_schedule/recent_schedules 필드명은 이미 배포된 홈 화면
    계약이라 Trip 전환 이후에도 그대로 유지되어야 한다.
    """
    service = HomeService(db=MagicMock())
    draft = _fake_trip(status="draft")
    recent = [_fake_trip(status="completed"), _fake_trip(status="completed")]

    service.trips = MagicMock()
    service.trips.get_in_progress.return_value = draft
    service.trips.get_recent.return_value = recent
    service.trip_places = MagicMock()
    service.guides = MagicMock()
    service.guides.get_top_public.return_value = None
    service.trip_places.count_by_trips.return_value = {
        draft.id: 4, recent[0].id: 4, recent[1].id: 4
    }

    current_user = CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")
    response = service.get_home(current_user)

    assert response.draft_schedule is not None
    assert response.draft_schedule.schedule_id == draft.id
    assert response.draft_schedule.title == draft.title
    assert response.draft_schedule.travel_date == draft.travel_date
    assert response.draft_schedule.status == "draft"
    assert response.draft_schedule.region_name == "제주"
    assert response.draft_schedule.place_count == 4
    assert response.draft_schedule.resume_url == f"/trips/{draft.id}/places"

    assert len(response.recent_schedules) == 2
    assert response.recent_schedules[0].schedule_id == recent[0].id
    assert response.recent_schedules[0].resume_url == f"/trips/{recent[0].id}/saved"

    service.trips.get_recent.assert_called_once_with(current_user.id, exclude_id=draft.id)


def test_get_home_without_draft_trip_returns_none_and_excludes_nothing():
    service = HomeService(db=MagicMock())
    service.trips = MagicMock()
    service.trips.get_in_progress.return_value = None
    service.trips.get_recent.return_value = []
    service.guides = MagicMock()
    service.guides.get_top_public.return_value = None

    current_user = CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")
    response = service.get_home(current_user)

    assert response.draft_schedule is None
    assert response.recent_schedules == []
    service.trips.get_recent.assert_called_once_with(current_user.id, exclude_id=None)


def test_get_home_includes_top_liked_public_guide_as_featured_guide():
    service = HomeService(db=MagicMock())
    service.trips = MagicMock()
    service.trips.get_in_progress.return_value = None
    service.trips.get_recent.return_value = []
    service.trip_places = MagicMock()
    service.trip_places.count_by_trips.return_value = {}
    link = MagicMock(token="tok123")
    trip = _fake_trip(title="대전 여행")
    region = MagicMock()
    region.name = "대전"
    service.guides = MagicMock()
    service.guides.get_top_public.return_value = (link, trip, region, 7)

    response = service.get_home(CurrentUser(id=uuid4(), email="t@example.com", nickname="t"))

    assert response.featured_guide is not None
    assert response.featured_guide.token == "tok123"
    assert response.featured_guide.title == "대전 여행"
    assert response.featured_guide.region_name == "대전"
    assert response.featured_guide.like_count == 7


def test_get_home_featured_guide_is_none_without_public_guides():
    service = HomeService(db=MagicMock())
    service.trips = MagicMock()
    service.trips.get_in_progress.return_value = None
    service.trips.get_recent.return_value = []
    service.trip_places = MagicMock()
    service.trip_places.count_by_trips.return_value = {}
    service.guides = MagicMock()
    service.guides.get_top_public.return_value = None

    response = service.get_home(CurrentUser(id=uuid4(), email="t@example.com", nickname="t"))

    assert response.featured_guide is None
