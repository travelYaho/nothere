"""방문 목적 태그 조회/저장(다중선택, 전체 교체) 비즈니스 로직을 담당한다."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.repositories.experience_tag_repository import ExperienceTagRepository
from app.repositories.trip_place_purpose_repository import TripPlacePurposeRepository
from app.repositories.trip_place_repository import TripPlaceRepository
from app.schemas.purpose import (
    PurposeGetResponse,
    PurposePutRequest,
    PurposePutResponse,
    PurposeTagResponse,
)
from app.schemas.user import CurrentUser


class PurposeService:
    """purpose 라우터가 호출하는 검증/조합 로직을 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.trip_places = TripPlaceRepository(db)
        self.purposes = TripPlacePurposeRepository(db)
        self.experience_tags = ExperienceTagRepository(db)

    def get_purpose(self, current_user: CurrentUser, trip_place_id: UUID) -> PurposeGetResponse:
        trip_place = self._get_owned_trip_place_or_404(current_user, trip_place_id)
        rows = self.purposes.list_by_trip_place(trip_place.id)
        tag_ids = [row.purpose_tag_id for row in rows]
        return PurposeGetResponse(
            trip_place_id=trip_place.id,
            purpose_tags=self._to_purpose_tags(tag_ids),
        )

    def replace_purpose(
        self,
        current_user: CurrentUser,
        trip_place_id: UUID,
        payload: PurposePutRequest,
    ) -> PurposePutResponse:
        trip_place = self._get_owned_trip_place_or_404(current_user, trip_place_id)

        # 체크박스형 다중선택 UI에서는 중복이 나올 일이 없지만, 방어적으로
        # 순서를 유지한 채 중복만 제거한다(안 하면 복합키 제약 위반으로 500이 난다).
        tag_ids = list(dict.fromkeys(payload.purpose_tag_ids))

        if tag_ids and len(self.experience_tags.get_active_by_ids(tag_ids)) != len(tag_ids):
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "선택한 방문 목적 태그를 찾을 수 없습니다.",
                status_code=404,
            )

        self.purposes.replace_all(trip_place.id, tag_ids)

        return PurposePutResponse(
            trip_place_id=trip_place.id,
            purpose_tags=self._to_purpose_tags(tag_ids),
            updated_at=datetime.now(timezone.utc),
        )

    def _get_owned_trip_place_or_404(self, current_user: CurrentUser, trip_place_id: UUID):
        trip_place = self.trip_places.get_owned_by_id(trip_place_id, current_user.id)
        if trip_place is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "장소를 찾을 수 없습니다.",
                status_code=404,
            )
        return trip_place

    def _to_purpose_tags(self, tag_ids: list[int]) -> list[PurposeTagResponse]:
        if not tag_ids:
            return []
        # is_active 필터 없이 조회한다 — 이미 저장된 선택이 나중에 태그가
        # 비활성화됐다고 응답에서 사라지면 안 된다.
        tags_by_id = {tag.id: tag for tag in self.experience_tags.get_by_ids(tag_ids)}
        return [
            PurposeTagResponse(id=tag_id, name=tags_by_id[tag_id].name)
            for tag_id in tag_ids
            if tag_id in tags_by_id
        ]
