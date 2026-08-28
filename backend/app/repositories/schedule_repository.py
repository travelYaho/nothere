"""홈 화면 요약에 필요한 일정 조회 쿼리를 모아 둔 repository 이다."""
from uuid import UUID

from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import Session

from app.db.models.schedule import IN_PROGRESS_STATUSES, Schedule


# [1주차 범위] 일정 CRUD가 아닌 GET /api/home 요약 조회 전용 repository.
# 일정 생성/상세/삭제 API는 이번 주에 구현하지 않는다.
class ScheduleRepository:
    """로그인 사용자 기준 진행 중/최근 일정만 조회한다."""
    def __init__(self, db: Session) -> None:
        self.db = db

    # 진행 중 일정 1건: DRAFT/ANALYZED/EDITING 중 updated_at 최신 (홈 draftSchedule용)
    def get_in_progress(self, user_id: UUID) -> Schedule | None:
        return (
            self.db.query(Schedule)
            .filter(Schedule.user_id == user_id, Schedule.status.in_(IN_PROGRESS_STATUSES))
            .order_by(desc(Schedule.updated_at))
            .first()
        )

    # 최근 일정 목록: 진행 중 제외, travel_date/updated_at 내림차순 (홈 recentSchedules용)
    def get_recent(
        self,
        user_id: UUID,
        exclude_id: UUID | None = None,
        limit: int = 5,
    ) -> list[Schedule]:
        query = (
            self.db.query(Schedule)
            .filter(
                Schedule.user_id == user_id,
                ~Schedule.status.in_(IN_PROGRESS_STATUSES),
            )
        )
        if exclude_id is not None:
            query = query.filter(Schedule.id != exclude_id)
        return (
            query.order_by(nulls_last(desc(Schedule.travel_date)), desc(Schedule.updated_at))
            .limit(limit)
            .all()
        )
