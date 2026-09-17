"""가이드북 공개 갤러리/좋아요 API 의 요청/응답 스키마를 정의한다."""
from uuid import UUID

from app.schemas.common import APIModel


class GuideCardResponse(APIModel):
    """탐색/좋아요/내 목록 한 칸에 해당하는 가이드북 카드.

    trip_id 는 "내가 만든" 목록에서 공유 여부와 무관하게 내 가이드북
    (GET /trips/{tripId}/guide)으로 이동하는 데 쓴다. token 은 공유 링크가
    있을 때만 채워진다(탐색/좋아요 카드는 항상 있음, 내 카드는 없을 수 있음).
    """
    trip_id: UUID
    token: str | None
    title: str
    region_name: str
    place_count: int
    tags: list[str]
    author_nickname: str
    cover_image_url: str | None
    like_count: int
    is_liked_by_me: bool


class ExploreDataResponse(APIModel):
    """GET /guides/explore 200 응답."""
    guides: list[GuideCardResponse]
    page: int
    has_next: bool
    total_count: int


class FilterOption(APIModel):
    """지역/태그 필터 선택지 한 건."""
    id: int
    name: str


class FiltersDataResponse(APIModel):
    """GET /guides/filters 200 응답."""
    regions: list[FilterOption]
    tags: list[FilterOption]


class LikeToggleResponse(APIModel):
    """POST|DELETE /guides/{token}/like 200 응답."""
    token: str
    like_count: int
    is_liked_by_me: bool
