"""STEP2(조건입력) 완료 시 여행(Trip)을 생성하는 비즈니스 로직을 담당한다."""
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.repositories.experience_tag_repository import ExperienceTagRepository
from app.repositories.region_repository import RegionRepository
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import TripCreateRequest, TripCreateResponse
from app.schemas.user import CurrentUser

_MIN_PREFERRED_TAGS = 2
_MAX_PREFERRED_TAGS = 3
_PREFERRED_TAG_WEIGHTS = (1.0, 0.7, 0.5)  # 1순위/2순위/3순위 (클릭 순서 기준)

_COMPANION_LABELS = {
    "solo": "혼자",
    "couple": "커플",
    "family": "가족",
    "friends": "친구",
}


def _generate_title(travel_date: date, companion_type: str | None) -> str:
    """title 미입력 시 'YYYY.MM.DD 동행유형 여행' 형태로 자동 생성한다."""
    label = _COMPANION_LABELS.get(companion_type or "", "")
    suffix = f"{label} 여행" if label else "여행"
    return f"{travel_date.strftime('%Y.%m.%d')} {suffix}"


class TripService:
    """STEP2 라우터가 호출하는 Trip 생성 검증/조합 로직을 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripRepository(db)
        self.regions = RegionRepository(db)
        self.experience_tags = ExperienceTagRepository(db)

    def create_trip(self, current_user: CurrentUser, payload: TripCreateRequest) -> TripCreateResponse:
        tag_ids = payload.preferred_experience_tag_ids
        has_duplicates = len(tag_ids) != len(set(tag_ids))
        if has_duplicates or not (_MIN_PREFERRED_TAGS <= len(tag_ids) <= _MAX_PREFERRED_TAGS):
            raise AppError(
                ErrorCode.INVALID_PREFERRED_EXPERIENCE_COUNT,
                f"선호 경험은 중복 없이 {_MIN_PREFERRED_TAGS}~{_MAX_PREFERRED_TAGS}개 선택해야 합니다.",
                status_code=400,
            )

        if payload.travel_date < date.today():
            raise AppError(
                ErrorCode.INVALID_TRAVEL_DATE,
                "여행 날짜는 오늘 이후여야 합니다.",
                status_code=400,
            )

        if self.regions.get_supported_by_id(payload.region_id) is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "선택한 지역을 찾을 수 없습니다.",
                status_code=404,
            )

        if len(self.experience_tags.get_active_by_ids(tag_ids)) != len(tag_ids):
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "선택한 선호 경험 태그를 찾을 수 없습니다.",
                status_code=404,
            )

        title = payload.title or _generate_title(payload.travel_date, payload.companion_type)

        trip = self.trips.create_trip(
            user_id=current_user.id,
            region_id=payload.region_id,
            title=title,
            travel_date=payload.travel_date,
            companion_type=payload.companion_type,
            transport_mode=payload.transport_mode,
            extra_time_limit_minutes=payload.extra_time_limit_minutes,
            preferred_experience_tag_ids=tag_ids,
            preferred_experience_weights=_PREFERRED_TAG_WEIGHTS,
        )

        return TripCreateResponse(
            trip_id=trip.id,
            title=trip.title,
            status=trip.status,
            current_step=trip.current_step,
            created_at=trip.created_at,
        )
