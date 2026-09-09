"""공유 가이드북 공개 조회."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.recommendation.service import RecommendationService
from app.schemas.envelope import ok

router = APIRouter(tags=["guide"])


@router.get("/guide/{token}")
def public_guide(token: str, db: Session = Depends(get_db)):
    data = RecommendationService(db).get_guide_by_token(token)
    return ok(data)
