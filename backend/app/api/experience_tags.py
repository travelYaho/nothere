"""STEP5(방문 목적 선택) UI가 쓰는 경험 태그 목록 조회. 인증 불필요한 정적 조회다."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models.experience_tag import ExperienceTag
from app.db.session import get_db
from app.schemas.envelope import ok

router = APIRouter(tags=["experience-tags"])


@router.get("/experience-tags")
def list_experience_tags(db: Session = Depends(get_db)):
    rows = (
        db.query(ExperienceTag)
        .filter(ExperienceTag.is_active.is_(True))
        .order_by(ExperienceTag.id.asc())
        .all()
    )
    data = [{"id": row.id, "code": row.code, "name": row.name} for row in rows]
    return ok(data)
