"""홈 화면 요약에 필요한 Trip 조회 쿼리를 모아 둔 repository 이다."""
from uuid import UUID

from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import Session

from app.db.models.trip import IN_PROGRESS_STATUSES, Trip


# [1주차 범위] Trip CRUD가 아닌 GET /api/home 요약 조회 전용 repository.
# STEP2~STEP9 전체 Trip API는 별도 이슈(도메인 라우터/서비스)에서 구현한다.
class TripRepository:
    """로그인 사용자 기준 진행 중/최근 여행만 조회한다."""
    def __init__(self, db: Session) -> None:
        self.db = db

    # 진행 중 여행 1건: DRAFT/ANALYZED/EDITING 중 updated_at 최신 (홈 draftSchedule용)
    def get_in_progress(self, user_id: UUID) -> Trip | None:
        return (
            self.db.query(Trip)
            .filter(Trip.user_id == user_id, Trip.status.in_(IN_PROGRESS_STATUSES))
            .order_by(desc(Trip.updated_at))
            .first()
        )

    # 최근 여행 목록: 진행 중 제외, travel_date/updated_at 내림차순 (홈 recentSchedules용)
    def get_recent(
        self,
        user_id: UUID,
        exclude_id: UUID | None = None,
        limit: int = 5,
    ) -> list[Trip]:
        query = (
            self.db.query(Trip)
            .filter(
                Trip.user_id == user_id,
                ~Trip.status.in_(IN_PROGRESS_STATUSES),
            )
        )
        if exclude_id is not None:
            query = query.filter(Trip.id != exclude_id)
        return (
            query.order_by(nulls_last(desc(Trip.travel_date)), desc(Trip.updated_at))
            .limit(limit)
            .all()
        )
