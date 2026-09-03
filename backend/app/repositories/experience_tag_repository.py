"""experience_tags 테이블에 대한 SQLAlchemy 접근을 모아 둔 repository 이다."""
from sqlalchemy.orm import Session

from app.db.models.experience_tag import ExperienceTag


class ExperienceTagRepository:
    """활성화된 선호 경험 태그(is_active=true) 조회를 담당한다."""
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active(self) -> list[ExperienceTag]:
        """STEP2/방문목적 UI에 노출할 순서(display_order) 그대로 반환한다."""
        return (
            self.db.query(ExperienceTag)
            .filter(ExperienceTag.is_active.is_(True))
            .order_by(ExperienceTag.display_order, ExperienceTag.id)
            .all()
        )

    def get_active_by_ids(self, ids: list[int]) -> list[ExperienceTag]:
        """Trip 생성 시 preferredExperienceTagIds 유효성 검사에 쓰는 다건 조회."""
        if not ids:
            return []
        return (
            self.db.query(ExperienceTag)
            .filter(ExperienceTag.id.in_(ids), ExperienceTag.is_active.is_(True))
            .all()
        )
