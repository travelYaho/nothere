"""가이드북 탐색/필터/좋아요 라우터를 dependency override 로 검증한다."""
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
    fake_user = CurrentUser(id=uuid4(), email="tester@example.com", nickname="테스터")
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield
    app.dependency_overrides.clear()


def test_explore_returns_mapped_guides(client):
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        from app.repositories.guide_repository import GuideCard

        MockRepo.return_value.list_public.return_value = (
            [
                GuideCard(
                    trip_id=uuid4(),
                    token="abc123XYZ",
                    title="서울 서촌 당일치기",
                    region_name="서울",
                    place_count=5,
                    tag_names=["역사", "문화"],
                    author_nickname="민서",
                    cover_image_url=None,
                    like_count=342,
                    is_liked_by_me=False,
                )
            ],
            1,
        )

        res = client.get("/api/guides/explore?sort=popular")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["page"] == 1
    assert body["hasNext"] is False
    assert body["guides"][0]["token"] == "abc123XYZ"
    assert body["guides"][0]["likeCount"] == 342
    assert body["guides"][0]["isLikedByMe"] is False


def test_explore_parses_comma_separated_tag_ids(client):
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.list_public.return_value = ([], 0)

        client.get("/api/guides/explore?tagIds=5,8&regionId=3&page=2&sort=recent&liked=true")

        MockRepo.return_value.list_public.assert_called_once()
        _, kwargs = MockRepo.return_value.list_public.call_args
        assert kwargs["tag_ids"] == [5, 8]
        assert kwargs["region_id"] == 3
        assert kwargs["page"] == 2
        assert kwargs["sort"] == "recent"
        assert kwargs["liked_only"] is True


def test_my_guides_returns_owned_guides(client):
    trip_id = uuid4()
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        from app.repositories.guide_repository import GuideCard

        MockRepo.return_value.list_owned.return_value = (
            [
                GuideCard(
                    trip_id=trip_id,
                    token="mine123",
                    title="내가 만든 서울 코스",
                    region_name="서울",
                    place_count=3,
                    tag_names=["맛집"],
                    author_nickname="테스터",
                    cover_image_url=None,
                    like_count=1,
                    is_liked_by_me=False,
                )
            ],
            1,
        )

        res = client.get("/api/guides/mine")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["page"] == 1
    assert body["guides"][0]["token"] == "mine123"
    assert body["guides"][0]["tripId"] == str(trip_id)
    MockRepo.return_value.list_owned.assert_called_once()
    _, kwargs = MockRepo.return_value.list_owned.call_args
    assert kwargs["page"] == 1


def test_my_guides_unshared_trip_has_null_token(client):
    """공유 링크를 한 번도 안 만든 확정 트립도 목록엔 나와야 하고, token 은 null 이어야 한다."""
    trip_id = uuid4()
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        from app.repositories.guide_repository import GuideCard

        MockRepo.return_value.list_owned.return_value = (
            [
                GuideCard(
                    trip_id=trip_id,
                    token=None,
                    title="아직 공유 안 한 부산 여행",
                    region_name="부산",
                    place_count=2,
                    tag_names=[],
                    author_nickname="테스터",
                    cover_image_url=None,
                    like_count=0,
                    is_liked_by_me=False,
                )
            ],
            1,
        )

        res = client.get("/api/guides/mine")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["guides"][0]["token"] is None
    assert body["guides"][0]["tripId"] == str(trip_id)
    assert body["guides"][0]["likeCount"] == 0


def test_filters_returns_regions_and_tags(client):
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        region = MagicMock(id=1)
        region.name = "서울"
        tag = MagicMock(id=5)
        tag.name = "맛집"
        MockRepo.return_value.list_filter_regions.return_value = [region]
        MockRepo.return_value.list_filter_tags.return_value = [tag]

        res = client.get("/api/guides/filters")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body["regions"] == [{"id": 1, "name": "서울"}]
    assert body["tags"] == [{"id": 5, "name": "맛집"}]


def test_like_guide_success(client):
    link = MagicMock(id=uuid4(), token="abc123XYZ", visibility="public", revoked_at=None, expires_at=None)
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = link
        MockRepo.is_share_link_gone.return_value = False
        MockRepo.return_value.count_likes.return_value = 13
        MockRepo.return_value.is_liked.return_value = True

        res = client.post("/api/guides/abc123XYZ/like")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body == {"token": "abc123XYZ", "likeCount": 13, "isLikedByMe": True}


def test_unlike_guide_success(client):
    link = MagicMock(id=uuid4(), token="abc123XYZ", visibility="public", revoked_at=None, expires_at=None)
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = link
        MockRepo.is_share_link_gone.return_value = False
        MockRepo.return_value.count_likes.return_value = 12
        MockRepo.return_value.is_liked.return_value = False

        res = client.delete("/api/guides/abc123XYZ/like")

    assert res.status_code == 200
    body = res.json()["data"]
    assert body == {"token": "abc123XYZ", "likeCount": 12, "isLikedByMe": False}


def test_like_guide_not_public_returns_403(client):
    link = MagicMock(id=uuid4(), token="abc123XYZ", visibility="link", revoked_at=None, expires_at=None)
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = link
        MockRepo.is_share_link_gone.return_value = False

        res = client.post("/api/guides/abc123XYZ/like")

    assert res.status_code == 403
    assert res.json()["error"]["code"] == "GUIDE_NOT_PUBLIC"


def test_like_guide_unknown_token_returns_404(client):
    with patch("app.services.guide_service.GuideRepository") as MockRepo:
        MockRepo.return_value.get_share_by_token.return_value = None

        res = client.post("/api/guides/no-such-token/like")

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
