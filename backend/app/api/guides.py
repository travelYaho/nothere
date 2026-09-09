"""가이드북 공개 갤러리 탐색/필터/좋아요 엔드포인트를 정의한다."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.guide import ExploreDataResponse, FiltersDataResponse, LikeToggleResponse
from app.schemas.user import CurrentUser
from app.services.guide_service import GuideService

router = APIRouter(prefix="/guides", tags=["guides"])


def _parse_tag_ids(tag_ids: str | None) -> list[int]:
    if not tag_ids:
        return []
    return [int(part) for part in tag_ids.split(",") if part.strip()]


@router.get("/explore", response_model=ApiResponse[ExploreDataResponse])
def explore_guides(
    sort: Literal["popular", "recent"] = "popular",
    region_id: int | None = Query(default=None, alias="regionId"),
    tag_ids: str | None = Query(default=None, alias="tagIds"),
    page: int = Query(default=1, ge=1),
    liked: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ExploreDataResponse]:
    """공개(visibility=public) 가이드북을 정렬/지역/태그로 필터링해 페이지 단위로 반환한다."""
    return ApiResponse(
        data=GuideService(db).explore(
            current_user,
            sort=sort,
            region_id=region_id,
            tag_ids=_parse_tag_ids(tag_ids),
            page=page,
            liked_only=liked,
        )
    )


@router.get("/filters", response_model=ApiResponse[FiltersDataResponse])
def guide_filters(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[FiltersDataResponse]:
    """탐색 화면 필터 시트에 노출할 지역/태그 선택지를 반환한다."""
    return ApiResponse(data=GuideService(db).filters())


@router.post("/{token}/like", response_model=ApiResponse[LikeToggleResponse])
def like_guide(
    token: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[LikeToggleResponse]:
    """가이드북에 좋아요를 추가한다. 이미 눌렀다면 멱등하게 200을 반환한다."""
    return ApiResponse(data=GuideService(db).like(current_user, token))


@router.delete("/{token}/like", response_model=ApiResponse[LikeToggleResponse])
def unlike_guide(
    token: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[LikeToggleResponse]:
    """가이드북 좋아요를 취소한다."""
    return ApiResponse(data=GuideService(db).unlike(current_user, token))
