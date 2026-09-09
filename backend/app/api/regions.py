"""STEP2 지역 선택 목록 조회 엔드포인트를 정의한다."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.region_repository import RegionRepository
from app.schemas.common import ApiResponse
from app.schemas.region import RegionListResponse, RegionResponse
from app.schemas.user import CurrentUser

router = APIRouter(tags=["regions"])


@router.get("/regions", response_model=ApiResponse[RegionListResponse])
def list_regions(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[RegionListResponse]:
    """MVP 지원 지역(isSupported=true) 목록을 반환한다."""
    regions = RegionRepository(db).list_supported()
    return ApiResponse(
        data=RegionListResponse(
            regions=[RegionResponse(id=region.id, name=region.name) for region in regions]
        )
    )
