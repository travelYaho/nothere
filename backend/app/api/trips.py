"""Trip 액션: remaining-congested, confirm, guide, share-link."""
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.analysis.service import AnalysisService
from app.domains.recommendation.service import RecommendationService
from app.schemas.envelope import ok
from app.schemas.recommendation import ShareLinkRequest
from app.schemas.user import CurrentUser

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/{trip_id}/analysis")
def run_analysis(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """STEP4 — 일정 내 모든 장소의 집중도를 분석해 저장하고 결과를 반환한다."""
    data = AnalysisService(db).run_analysis(current_user, trip_id)
    return ok(data)


@router.get("/{trip_id}/analysis")
def get_analysis(
    trip_id: UUID,
    status: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """저장된 분석 결과를 조회한다. status=CROWDED 면 아직 미해결인 혼잡 장소만 반환한다."""
    data = AnalysisService(db).get_analysis(current_user, trip_id, status)
    return ok(data)


@router.get("/{trip_id}/remaining-congested")
def remaining_congested(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).remaining_congested(trip_id, current_user)
    return ok(data)


@router.post("/{trip_id}/confirm")
def confirm_trip(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).confirm(trip_id, current_user)
    return ok(data)


@router.get("/{trip_id}/guide")
def trip_guide(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).get_guide(trip_id, current_user)
    return ok(data)


@router.post("/{trip_id}/share-link", status_code=status.HTTP_201_CREATED)
def share_link(
    trip_id: UUID,
    payload: ShareLinkRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = payload or ShareLinkRequest()
    data = RecommendationService(db).create_share_link(
        trip_id, current_user, body.visibility
    )
    return ok(data)
