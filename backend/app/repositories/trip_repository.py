"""Trip 생성 및 홈 화면 요약에 필요한 조회 쿼리를 모아 둔 repository 이다."""
from datetime import date
from uuid import UUID

from sqlalchemy import desc, func, nulls_last, select
from sqlalchemy.orm import Session

from app.db.models.preference import TripPreferredExperience
from app.db.models.trip import IN_PROGRESS_STATUSES, Trip
from app.db.models.trip_place import TripPlace

_CONDITION_FIELDS = (
    "title",
    "travel_date",
    "region_id",
    "companion_type",
    "transport_mode",
    "extra_time_limit_minutes",
)

PAGE_SIZE = 10


def _recency_expr():
    """"최근 작업 순" 정렬 기준. Trip.updated_at 은 장소 추가/삭제/방문시간
    수정처럼 TripPlace 만 바뀌는 액션에서는 안 갱신되므로(그 액션들은 trip
    행 자체를 건드리지 않는다), 등록된 장소 중 가장 최근에 손댄 시각과
    비교해 더 늦은 쪽을 쓴다.
    """
    latest_place_update = (
        select(func.max(TripPlace.updated_at))
        .where(TripPlace.trip_id == Trip.id)
        .correlate(Trip)
        .scalar_subquery()
    )
    return func.greatest(Trip.updated_at, func.coalesce(latest_place_update, Trip.updated_at))


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

    def get_owned_by_id(self, trip_id: UUID, user_id: UUID) -> Trip | None:
        """PATCH/DELETE 전, 해당 사용자 소유의 Trip 인지까지 함께 확인한다."""
        return (
            self.db.query(Trip)
            .filter(Trip.id == trip_id, Trip.user_id == user_id)
            .first()
        )

    def mark_needs_reanalysis(self, trip: Trip) -> Trip:
        """장소 순서변경처럼 무조건 재분석이 필요해지는 액션에 쓴다."""
        trip.needs_reanalysis = True
        self.db.commit()
        self.db.refresh(trip)
        return trip

    def update_conditions(
        self,
        trip: Trip,
        *,
        fields: dict,
        needs_reanalysis: bool,
        preferred_experience_tag_ids: list[int] | None,
        preferred_experience_weights: tuple[float, ...],
    ) -> Trip:
        """제공된 필드만 갱신한다. preferred_experience_tag_ids 가 주어지면
        기존 선호경험을 전체 교체한다(cascade="all, delete-orphan").
        """
        for field_name in _CONDITION_FIELDS:
            if field_name in fields:
                setattr(trip, field_name, fields[field_name])
        trip.needs_reanalysis = needs_reanalysis

        if preferred_experience_tag_ids is not None:
            trip.preferred_experiences = [
                TripPreferredExperience(experience_tag_id=tag_id, weight=weight)
                for tag_id, weight in zip(preferred_experience_tag_ids, preferred_experience_weights)
            ]

        self.db.commit()
        self.db.refresh(trip)
        return trip

    def delete(self, trip: Trip) -> None:
        """하드 삭제. TripPlace/TripPreferredExperience 등은 FK cascade 로 함께 삭제된다."""
        self.db.delete(trip)
        self.db.commit()

    # 진행 중 여행 1건: DRAFT/ANALYZED/EDITING 중 최근 작업순 (홈 draftSchedule용)
    def get_in_progress(self, user_id: UUID) -> Trip | None:
        return (
            self.db.query(Trip)
            .filter(Trip.user_id == user_id, Trip.status.in_(IN_PROGRESS_STATUSES))
            .order_by(desc(_recency_expr()))
            .first()
        )

    # 최근 여행 목록: 진행 중 제외, travel_date 내림차순(동률이면 최근 작업순) (홈 recentSchedules용)
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
            query.order_by(nulls_last(desc(Trip.travel_date)), desc(_recency_expr()))
            .limit(limit)
            .all()
        )

    # 보관함 "일정" 탭용 목록 조회. status_filter 는 "draft"(작성 중, IN_PROGRESS_STATUSES)
    # 또는 "confirmed"(그 외) 중 하나이거나, None 이면 전체.
    def list_by_user(
        self,
        user_id: UUID,
        *,
        status_filter: str | None,
        page: int,
    ) -> tuple[list[Trip], int]:
        query = self.db.query(Trip).filter(Trip.user_id == user_id)
        if status_filter == "draft":
            query = query.filter(Trip.status.in_(IN_PROGRESS_STATUSES))
        elif status_filter == "confirmed":
            query = query.filter(~Trip.status.in_(IN_PROGRESS_STATUSES))

        total_count = query.count()
        rows = (
            query.order_by(desc(_recency_expr()))
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
            .all()
        )
        return rows, total_count

    # 마이페이지 통계: (일정 생성을 시작한 전체 Trip 수, 확정까지 간 적 있는 Trip 수)
    def count_stats(self, user_id: UUID) -> tuple[int, int]:
        total = (
            self.db.query(func.count(Trip.id)).filter(Trip.user_id == user_id).scalar()
        )
        confirmed = (
            self.db.query(func.count(Trip.id))
            .filter(Trip.user_id == user_id, Trip.confirmed_at.isnot(None))
            .scalar()
        )
        return total or 0, confirmed or 0
