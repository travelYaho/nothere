"""Trip 생성 및 홈 화면 요약에 필요한 조회 쿼리를 모아 둔 repository 이다."""
from datetime import date
from uuid import UUID

from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import Session

from app.db.models.trip import IN_PROGRESS_STATUSES, Trip, TripPreferredExperience


class TripRepository:
    """로그인 사용자 기준 Trip 생성/조회를 담당한다."""
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_trip(
        self,
        *,
        user_id: UUID,
        region_id: int,
        title: str,
        travel_date: date,
        companion_type: str | None,
        transport_mode: str | None,
        extra_time_limit_minutes: int | None,
        preferred_experience_tag_ids: list[int],
        preferred_experience_weights: tuple[float, ...],
    ) -> Trip:
        """STEP2 입력 완료 시 Trip + TripPreferredExperience 를 함께 생성한다.

        STEP2 완료는 곧 STEP3 진입이므로 current_step 은 컬럼 기본값(2)이
        아니라 3으로 명시한다(API 명세서 POST /trips 응답 예시 기준).
        """
        trip = Trip(
            user_id=user_id,
            region_id=region_id,
            title=title,
            travel_date=travel_date,
            companion_type=companion_type,
            transport_mode=transport_mode,
            extra_time_limit_minutes=extra_time_limit_minutes,
            current_step=3,
        )
        trip.preferred_experiences = [
            TripPreferredExperience(experience_tag_id=tag_id, weight=weight)
            for tag_id, weight in zip(preferred_experience_tag_ids, preferred_experience_weights)
        ]
        self.db.add(trip)
        self.db.commit()
        self.db.refresh(trip)
        return trip

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
