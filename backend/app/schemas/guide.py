"""가이드북 공개 갤러리/좋아요 API 의 요청/응답 스키마를 정의한다."""
from app.schemas.common import APIModel


class GuideCardResponse(APIModel):
    """탐색/좋아요 목록 한 칸에 해당하는 가이드북 카드."""
    token: str
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
