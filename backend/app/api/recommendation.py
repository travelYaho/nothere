"""추천 경로 점수·후보 조회 API."""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.recommendation.service import RecommendationService
from app.schemas.envelope import ok
from app.schemas.recommendation import RouteScoreRequest
from app.schemas.user import CurrentUser

router = APIRouter(tags=["recommendation"])


@router.post("/recommendation-requests/{request_id}/route-scores")
def score_routes(
    request_id: UUID,
    payload: RouteScoreRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = payload or RouteScoreRequest()
    data = RecommendationService(db).score_routes(
        request_id,
        current_user,
        transport_mode=body.transport_mode,
        extra_time_limit_minutes=body.extra_time_limit_minutes,
    )
    return ok(data)


@router.get("/recommendation-requests/{request_id}/candidates")
def get_scored_candidates(
    request_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).get_candidates(request_id, current_user)
    return ok(data)
