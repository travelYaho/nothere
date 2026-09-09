"""가이드북 공개 갤러리 조회·좋아요 비즈니스 로직을 담당한다."""
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.db.models.share_link import ShareLinkVisibility
from app.repositories.guide_repository import PAGE_SIZE, GuideRepository
from app.schemas.guide import (
    ExploreDataResponse,
    FilterOption,
    FiltersDataResponse,
    GuideCardResponse,
    LikeToggleResponse,
)
from app.schemas.user import CurrentUser


class GuideService:
    """guides 라우터가 호출하는 탐색/필터/좋아요 로직을 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.guides = GuideRepository(db)

    def explore(
        self,
        current_user: CurrentUser,
        *,
        sort: str,
        region_id: int | None,
        tag_ids: list[int],
        page: int,
        liked_only: bool,
    ) -> ExploreDataResponse:
        cards, total_count = self.guides.list_public(
            viewer_id=current_user.id,
            sort=sort,
            region_id=region_id,
            tag_ids=tag_ids,
            page=page,
            liked_only=liked_only,
        )
        return ExploreDataResponse(
            guides=[
                GuideCardResponse(
                    token=card.token,
                    title=card.title,
                    region_name=card.region_name,
                    place_count=card.place_count,
                    tags=card.tag_names,
                    author_nickname=card.author_nickname,
                    cover_image_url=card.cover_image_url,
                    like_count=card.like_count,
                    is_liked_by_me=card.is_liked_by_me,
                )
                for card in cards
            ],
            page=page,
            has_next=page * PAGE_SIZE < total_count,
            total_count=total_count,
        )

    def filters(self) -> FiltersDataResponse:
        return FiltersDataResponse(
            regions=[
                FilterOption(id=region.id, name=region.name)
                for region in self.guides.list_filter_regions()
            ],
            tags=[
                FilterOption(id=tag.id, name=tag.name)
                for tag in self.guides.list_filter_tags()
            ],
        )

    def like(self, current_user: CurrentUser, token: str) -> LikeToggleResponse:
        link = self._get_public_share_link(token)
        self.guides.add_like(link.id, current_user.id)
        return self._like_response(link.id, link.token, current_user.id)

    def unlike(self, current_user: CurrentUser, token: str) -> LikeToggleResponse:
        link = self._get_public_share_link(token)
        self.guides.remove_like(link.id, current_user.id)
        return self._like_response(link.id, link.token, current_user.id)

    def _get_public_share_link(self, token: str):
        link = self.guides.get_share_by_token(token)
        if link is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "공유 링크를 찾을 수 없습니다.",
                status_code=404,
            )
        if GuideRepository.is_share_link_gone(link):
            raise AppError(
                ErrorCode.SHARE_LINK_GONE,
                "만료되었거나 취소된 링크입니다.",
                status_code=410,
            )
        if link.visibility != ShareLinkVisibility.PUBLIC:
            raise AppError(
                ErrorCode.GUIDE_NOT_PUBLIC,
                "공개된 가이드북이 아닙니다.",
                status_code=403,
            )
        return link

    def _like_response(self, share_link_id, token: str, user_id) -> LikeToggleResponse:
        return LikeToggleResponse(
            token=token,
            like_count=self.guides.count_likes(share_link_id),
            is_liked_by_me=self.guides.is_liked(share_link_id, user_id),
        )
