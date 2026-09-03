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
        """Trip 생성/수정 시 태그 선택 유효성 검사에 쓰는 다건 조회(활성 태그만)."""
        if not ids:
            return []
        return (
            self.db.query(ExperienceTag)
            .filter(ExperienceTag.id.in_(ids), ExperienceTag.is_active.is_(True))
            .all()
        )

    def get_by_ids(self, ids: list[int]) -> list[ExperienceTag]:
        """이미 저장된 선택값을 표시할 때 쓰는 다건 조회(is_active 필터 없음).

        태그가 나중에 비활성화되더라도, 과거에 저장된 방문목적/선호경험 응답에서
        이름이 사라지면 안 되므로 활성 여부와 무관하게 조회한다.
        """
        if not ids:
            return []
        return self.db.query(ExperienceTag).filter(ExperienceTag.id.in_(ids)).all()
