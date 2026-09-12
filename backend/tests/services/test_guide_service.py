"""GuideService(탐색/필터/좋아요) 단위 테스트.

PlaceService 테스트와 같은 패턴으로 GuideRepository 를 통째로 모킹해
DB/Supabase 실접속 없이 서비스 계층의 분기 로직만 검증한다.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import AppError, ErrorCode
from app.db.models.share_link import ShareLinkVisibility
from app.repositories.guide_repository import GuideCard
from app.schemas.user import CurrentUser
from app.services.guide_service import GuideService


@pytest.fixture
def current_user() -> CurrentUser:
    return CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")


def _card(**overrides) -> GuideCard:
    defaults = dict(
        trip_id=uuid4(),
        token="abc123XYZ",
        title="경주 야경 명소만 모았어요",
        region_name="경주",
        place_count=4,
        tag_names=["사진", "전망"],
        author_nickname="수아",
        cover_image_url="https://example.com/cover.png",
        like_count=512,
        is_liked_by_me=False,
    )
    defaults.update(overrides)
    return GuideCard(**defaults)


def test_explore_maps_cards_and_sets_has_next_true_when_more_remain(current_user):
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.list_public.return_value = ([_card()], 9)

        result = GuideService(MagicMock()).explore(
            current_user, sort="popular", region_id=None, tag_ids=[], page=1, liked_only=False
        )

    assert result.page == 1
    assert result.total_count == 9
    assert result.has_next is True  # page(1) * PAGE_SIZE(8) = 8 < 9
    assert len(result.guides) == 1
    card = result.guides[0]
    assert card.token == "abc123XYZ"
    assert card.tags == ["사진", "전망"]
    assert card.author_nickname == "수아"


def test_explore_has_next_false_on_last_page(current_user):
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.list_public.return_value = ([_card()], 8)

        result = GuideService(MagicMock()).explore(
            current_user, sort="popular", region_id=None, tag_ids=[], page=1, liked_only=False
        )

    assert result.has_next is False


def test_explore_forwards_filters_to_repository(current_user):
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.list_public.return_value = ([], 0)

        GuideService(MagicMock()).explore(
            current_user, sort="recent", region_id=3, tag_ids=[5, 8], page=2, liked_only=True
        )

        MockRepo.return_value.list_public.assert_called_once_with(
            viewer_id=current_user.id,
            sort="recent",
            region_id=3,
            tag_ids=[5, 8],
            page=2,
            liked_only=True,
        )


def test_list_mine_maps_cards_and_forwards_owner_id(current_user):
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.list_owned.return_value = ([_card()], 3)

        result = GuideService(MagicMock()).list_mine(current_user, page=1)

        MockRepo.return_value.list_owned.assert_called_once_with(
            owner_id=current_user.id, page=1
        )

    assert result.page == 1
    assert result.total_count == 3
    assert result.has_next is False  # page(1) * PAGE_SIZE(8) = 8, not < 3
    assert len(result.guides) == 1
    assert result.guides[0].token == "abc123XYZ"


def test_filters_maps_regions_and_tags(current_user):
    region = MagicMock(id=1)
    region.name = "서울"
    tag = MagicMock(id=5)
    tag.name = "맛집"
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.list_filter_regions.return_value = [region]
        MockRepo.return_value.list_filter_tags.return_value = [tag]

        result = GuideService(MagicMock()).filters()

    assert result.regions == [_filter_option(1, "서울")]
    assert result.tags == [_filter_option(5, "맛집")]


def _filter_option(id_: int, name: str):
    from app.schemas.guide import FilterOption

    return FilterOption(id=id_, name=name)


def _mock_link(*, visibility=ShareLinkVisibility.PUBLIC, revoked_at=None, expires_at=None, token="abc123XYZ"):
    link = MagicMock()
    link.id = uuid4()
    link.token = token
    link.visibility = visibility
    link.revoked_at = revoked_at
    link.expires_at = expires_at
    return link


def test_like_adds_like_and_returns_updated_count(current_user):
    link = _mock_link()
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = link
        MockRepo.is_share_link_gone.return_value = False
        MockRepo.return_value.count_likes.return_value = 13
        MockRepo.return_value.is_liked.return_value = True

        result = GuideService(MagicMock()).like(current_user, "abc123XYZ")

    MockRepo.return_value.add_like.assert_called_once_with(link.id, current_user.id)
    assert result.like_count == 13
    assert result.is_liked_by_me is True


def test_unlike_removes_like_and_returns_updated_count(current_user):
    link = _mock_link()
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = link
        MockRepo.is_share_link_gone.return_value = False
        MockRepo.return_value.count_likes.return_value = 12
        MockRepo.return_value.is_liked.return_value = False

        result = GuideService(MagicMock()).unlike(current_user, "abc123XYZ")

    MockRepo.return_value.remove_like.assert_called_once_with(link.id, current_user.id)
    assert result.like_count == 12
    assert result.is_liked_by_me is False


def test_like_unknown_token_raises_resource_not_found(current_user):
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = None

        with pytest.raises(AppError) as exc_info:
            GuideService(MagicMock()).like(current_user, "no-such-token")

    assert exc_info.value.code == ErrorCode.RESOURCE_NOT_FOUND
    assert exc_info.value.status_code == 404


def test_like_revoked_link_raises_share_link_gone(current_user):
    link = _mock_link(revoked_at=datetime.now(timezone.utc))
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = link
        MockRepo.is_share_link_gone.return_value = True

        with pytest.raises(AppError) as exc_info:
            GuideService(MagicMock()).like(current_user, link.token)

    assert exc_info.value.code == ErrorCode.SHARE_LINK_GONE
    assert exc_info.value.status_code == 410


def test_like_expired_link_raises_share_link_gone(current_user):
    link = _mock_link(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = link
        MockRepo.is_share_link_gone.return_value = True

        with pytest.raises(AppError) as exc_info:
            GuideService(MagicMock()).like(current_user, link.token)

    assert exc_info.value.code == ErrorCode.SHARE_LINK_GONE


def test_like_non_public_link_raises_guide_not_public(current_user):
    link = _mock_link(visibility=ShareLinkVisibility.LINK)
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = link
        MockRepo.is_share_link_gone.return_value = False

        with pytest.raises(AppError) as exc_info:
            GuideService(MagicMock()).like(current_user, link.token)

    assert exc_info.value.code == ErrorCode.GUIDE_NOT_PUBLIC
    assert exc_info.value.status_code == 403


def test_unlike_non_public_link_raises_guide_not_public(current_user):
    link = _mock_link(visibility=ShareLinkVisibility.PRIVATE)
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = link
        MockRepo.is_share_link_gone.return_value = False

        with pytest.raises(AppError) as exc_info:
            GuideService(MagicMock()).unlike(current_user, link.token)

    assert exc_info.value.code == ErrorCode.GUIDE_NOT_PUBLIC
