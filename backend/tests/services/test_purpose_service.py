"""PurposeService.get_purpose / replace_purpose 를 repository mock 으로 검증한다."""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, ErrorCode
from app.schemas.purpose import PurposePutRequest
from app.schemas.user import CurrentUser
from app.services.purpose_service import PurposeService


def _tag(tag_id, name):
    t = MagicMock(id=tag_id)
    t.name = name  # MagicMock(name=...)는 예약어라 별도로 설정해야 한다.
    return t


def _service_with_mocks():
    service = PurposeService(db=MagicMock())
    service.trip_places = MagicMock()
    service.purposes = MagicMock()
    service.experience_tags = MagicMock()
    return service


def _current_user():
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")


# --- get_purpose ---

def test_get_purpose_returns_saved_tags_with_names():
    service = _service_with_mocks()
    trip_place_id = uuid4()
    service.trip_places.get_owned_by_id.return_value = MagicMock(id=trip_place_id)
    service.purposes.list_by_trip_place.return_value = [
        MagicMock(purpose_tag_id=6), MagicMock(purpose_tag_id=1)
    ]
    service.experience_tags.get_by_ids.return_value = [_tag(6, "카페·휴식"), _tag(1, "자연·산책")]

    result = service.get_purpose(_current_user(), trip_place_id)

    assert [t.id for t in result.purpose_tags] == [6, 1]
    assert result.purpose_tags[0].name == "카페·휴식"


def test_get_purpose_unknown_trip_place_returns_404():
    service = _service_with_mocks()
    service.trip_places.get_owned_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.get_purpose(_current_user(), uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND


def test_get_purpose_with_no_saved_tags_returns_empty_list():
    service = _service_with_mocks()
    service.trip_places.get_owned_by_id.return_value = MagicMock(id=uuid4())
    service.purposes.list_by_trip_place.return_value = []

    result = service.get_purpose(_current_user(), uuid4())

    assert result.purpose_tags == []
    service.experience_tags.get_by_ids.assert_not_called()


# --- replace_purpose ---

def test_replace_purpose_success_calls_replace_all_with_deduped_order():
    service = _service_with_mocks()
    trip_place_id = uuid4()
    service.trip_places.get_owned_by_id.return_value = MagicMock(id=trip_place_id)
    service.experience_tags.get_active_by_ids.return_value = [MagicMock(id=6), MagicMock(id=1)]
    service.experience_tags.get_by_ids.return_value = [_tag(6, "카페·휴식"), _tag(1, "자연·산책")]

    payload = PurposePutRequest(purpose_tag_ids=[6, 1])
    result = service.replace_purpose(_current_user(), trip_place_id, payload)

    service.purposes.replace_all.assert_called_once_with(trip_place_id, [6, 1])
    assert [t.id for t in result.purpose_tags] == [6, 1]


def test_replace_purpose_duplicate_ids_are_deduped_not_rejected():
    """체크박스 UI에서 안 나올 케이스지만, 나오면 중복 저장으로 500 나는 걸 막는다."""
    service = _service_with_mocks()
    trip_place_id = uuid4()
    service.trip_places.get_owned_by_id.return_value = MagicMock(id=trip_place_id)
    service.experience_tags.get_active_by_ids.return_value = [MagicMock(id=6)]
    service.experience_tags.get_by_ids.return_value = [_tag(6, "카페·휴식")]

    payload = PurposePutRequest(purpose_tag_ids=[6, 6, 6])
    service.replace_purpose(_current_user(), trip_place_id, payload)

    service.purposes.replace_all.assert_called_once_with(trip_place_id, [6])


def test_replace_purpose_with_empty_list_clears_all_selection():
    """방문목적은 0개 이상 — 빈 배열로 전체 해제가 가능해야 한다."""
    service = _service_with_mocks()
    trip_place_id = uuid4()
    service.trip_places.get_owned_by_id.return_value = MagicMock(id=trip_place_id)

    payload = PurposePutRequest(purpose_tag_ids=[])
    result = service.replace_purpose(_current_user(), trip_place_id, payload)

    service.purposes.replace_all.assert_called_once_with(trip_place_id, [])
    assert result.purpose_tags == []
    service.experience_tags.get_active_by_ids.assert_not_called()


def test_replace_purpose_unknown_tag_returns_404():
    service = _service_with_mocks()
    trip_place_id = uuid4()
    service.trip_places.get_owned_by_id.return_value = MagicMock(id=trip_place_id)
    service.experience_tags.get_active_by_ids.return_value = [MagicMock(id=6)]  # 2개 요청, 1개만 존재

    payload = PurposePutRequest(purpose_tag_ids=[6, 999])

    with pytest.raises(AppError) as exc_info:
        service.replace_purpose(_current_user(), trip_place_id, payload)

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND
    service.purposes.replace_all.assert_not_called()


def test_replace_purpose_unknown_trip_place_returns_404():
    service = _service_with_mocks()
    service.trip_places.get_owned_by_id.return_value = None

    with pytest.raises(AppError) as exc_info:
        service.replace_purpose(_current_user(), uuid4(), PurposePutRequest(purpose_tag_ids=[1]))

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND
