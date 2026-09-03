"""선호 경험 태그(10종) 목록 조회 엔드포인트를 정의한다."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.experience_tag_repository import ExperienceTagRepository
from app.schemas.common import ApiResponse
from app.schemas.experience_tag import ExperienceTagListResponse, ExperienceTagResponse
from app.schemas.user import CurrentUser

router = APIRouter(tags=["experience-tags"])


@router.get("/experience-tags", response_model=ApiResponse[ExperienceTagListResponse])
def list_experience_tags(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[ExperienceTagListResponse]:
    """활성화된 선호 경험 태그를 노출 순서(display_order)대로 반환한다."""
    tags = ExperienceTagRepository(db).list_active()
    return ApiResponse(
        data=ExperienceTagListResponse(
            experience_tags=[ExperienceTagResponse(id=tag.id, name=tag.name) for tag in tags]
        )
    )
