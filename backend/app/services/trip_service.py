"""STEP2(조건입력) 완료 시 여행(Trip)을 생성/수정/삭제하는 비즈니스 로직을 담당한다."""
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.repositories.experience_tag_repository import ExperienceTagRepository
from app.repositories.region_repository import RegionRepository
from app.repositories.trip_repository import TripRepository
from app.schemas.trip import (
    TripConditionsUpdateRequest,
    TripConditionsUpdateResponse,
    TripCreateRequest,
    TripCreateResponse,
    TripDetailResponse,
    TripPlaceDetail,
)
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


def _validate_preferred_tag_ids(tag_ids: list[int]) -> None:
    """생성/수정 공통: 선호 경험은 중복 없이 2~3개여야 한다."""
    has_duplicates = len(tag_ids) != len(set(tag_ids))
    if has_duplicates or not (_MIN_PREFERRED_TAGS <= len(tag_ids) <= _MAX_PREFERRED_TAGS):
        raise AppError(
            ErrorCode.INVALID_PREFERRED_EXPERIENCE_COUNT,
            f"선호 경험은 중복 없이 {_MIN_PREFERRED_TAGS}~{_MAX_PREFERRED_TAGS}개 선택해야 합니다.",
            status_code=400,
        )


class TripService:
    """STEP2 라우터가 호출하는 Trip 생성 검증/조합 로직을 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.trips = TripRepository(db)
        self.regions = RegionRepository(db)
        self.experience_tags = ExperienceTagRepository(db)

    def create_trip(self, current_user: CurrentUser, payload: TripCreateRequest) -> TripCreateResponse:
        tag_ids = payload.preferred_experience_tag_ids
        _validate_preferred_tag_ids(tag_ids)

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

    def _get_owned_trip_or_404(self, current_user: CurrentUser, trip_id: UUID):
        trip = self.trips.get_owned_by_id(trip_id, current_user.id)
        if trip is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "여행 일정을 찾을 수 없습니다.",
                status_code=404,
            )
        return trip

    def update_conditions(
        self,
        current_user: CurrentUser,
        trip_id: UUID,
        payload: TripConditionsUpdateRequest,
    ) -> TripConditionsUpdateResponse:
        trip = self._get_owned_trip_or_404(current_user, trip_id)
        fields = payload.model_dump(exclude_unset=True)

        tag_ids = fields.get("preferred_experience_tag_ids")
        if tag_ids is not None:
            _validate_preferred_tag_ids(tag_ids)
            if len(self.experience_tags.get_active_by_ids(tag_ids)) != len(tag_ids):
                raise AppError(
                    ErrorCode.RESOURCE_NOT_FOUND,
                    "선택한 선호 경험 태그를 찾을 수 없습니다.",
                    status_code=404,
                )

        new_travel_date = fields.get("travel_date")
        if new_travel_date is not None and new_travel_date < date.today():
            raise AppError(
                ErrorCode.INVALID_TRAVEL_DATE,
                "여행 날짜는 오늘 이후여야 합니다.",
                status_code=400,
            )

        warnings: list[str] = []
        new_region_id = fields.get("region_id")
        if new_region_id is not None and new_region_id != trip.region_id:
            if self.regions.get_supported_by_id(new_region_id) is None:
                raise AppError(
                    ErrorCode.RESOURCE_NOT_FOUND,
                    "선택한 지역을 찾을 수 없습니다.",
                    status_code=404,
                )
            if trip.trip_places:
                warnings.append(
                    "지역이 변경되어 기존에 등록된 장소가 새 지역과 맞지 않을 수 있습니다. "
                    "기존 장소는 자동으로 삭제되지 않으니 직접 확인해 주세요."
                )

        # travelDate/transportMode 변경 시에만 needsReanalysis=true 로 전환한다(API 명세서 기준).
        # 한 번 true 가 된 뒤 이 엔드포인트에서 다시 false 로 되돌리지는 않는다(재분석은 STEP4 담당).
        needs_reanalysis = trip.needs_reanalysis
        if "travel_date" in fields and new_travel_date != trip.travel_date:
            needs_reanalysis = True
        if "transport_mode" in fields and fields["transport_mode"] != trip.transport_mode:
            needs_reanalysis = True

        trip = self.trips.update_conditions(
            trip,
            fields=fields,
            needs_reanalysis=needs_reanalysis,
            preferred_experience_tag_ids=tag_ids,
            preferred_experience_weights=_PREFERRED_TAG_WEIGHTS,
        )

        return TripConditionsUpdateResponse(
            trip_id=trip.id,
            needs_reanalysis=trip.needs_reanalysis,
            warnings=warnings,
            updated_at=trip.updated_at,
        )

    def delete_trip(self, current_user: CurrentUser, trip_id: UUID) -> None:
        trip = self._get_owned_trip_or_404(current_user, trip_id)
        self.trips.delete(trip)

    def get_trip_detail(self, current_user: CurrentUser, trip_id: UUID) -> TripDetailResponse:
        """GET /trips/{tripId} — STEP3 화면 진입/새로고침 시 기존 상태를 복원한다."""
        trip = self._get_owned_trip_or_404(current_user, trip_id)

        # weight 내림차순 = 1/2/3순위 클릭 순서 복원(1.0/0.7/0.5).
        preferred_tag_ids = [
            pref.experience_tag_id
            for pref in sorted(trip.preferred_experiences, key=lambda p: p.weight, reverse=True)
        ]
        places = [
            TripPlaceDetail(
                trip_place_id=tp.id,
                place_id=tp.place_id,
                name=tp.place.name,
                visit_order=tp.position,
                visit_time=tp.visit_time,
                duration_minutes=tp.stay_minutes,
                is_fixed=tp.is_fixed,
            )
            for tp in trip.trip_places  # 관계에 order_by="TripPlace.position" 이미 설정됨
        ]

        return TripDetailResponse(
            trip_id=trip.id,
            title=trip.title,
            travel_date=trip.travel_date,
            region_id=trip.region_id,
            region_name=trip.region.name,
            companion_type=trip.companion_type,
            transport_mode=trip.transport_mode,
            extra_time_limit_minutes=trip.extra_time_limit_minutes,
            status=trip.status,
            current_step=trip.current_step,
            needs_reanalysis=trip.needs_reanalysis,
            preferred_experience_tag_ids=preferred_tag_ids,
            places=places,
        )
