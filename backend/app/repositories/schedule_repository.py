"""구 schedules repository — 테이블 폐기. trip 전환 시 교체 예정."""
from uuid import UUID

from sqlalchemy.orm import Session


class ScheduleRepository:
    """schedules / schedule_places 테이블이 제거되어 더 이상 사용하지 않는다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_in_progress(self, user_id: UUID):
        return None

    def list_recent(self, user_id: UUID, *, exclude_id: UUID | None = None, limit: int = 5):
        return []

    def list_by_user(self, user_id: UUID):
        return []

    def get_owned(self, schedule_id: UUID, user_id: UUID):
        return None
