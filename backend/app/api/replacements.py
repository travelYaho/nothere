"""교체 미리보기·적용·되돌리기 API."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.recommendation.service import RecommendationService
from app.schemas.envelope import ok
from app.schemas.recommendation import ReplacementCreateRequest, ReplacementPreviewRequest
from app.schemas.user import CurrentUser

router = APIRouter(tags=["replacements"])


@router.post("/trip-places/{trip_place_id}/replacement-preview")
def replacement_preview(
    trip_place_id: UUID,
    payload: ReplacementPreviewRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).replacement_preview(
        trip_place_id, payload.candidate_id, current_user
    )
    return ok(data)


@router.post("/replacements", status_code=status.HTTP_201_CREATED)
def create_replacement(
    payload: ReplacementCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).apply_replacement(
        payload.trip_place_id, payload.candidate_id, current_user
    )
    return ok(data)


@router.post("/replacements/{replacement_id}/revert")
def revert_replacement(
    replacement_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).revert_replacement(replacement_id, current_user)
    return ok(data)
