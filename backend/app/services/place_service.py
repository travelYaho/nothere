"""STEP3(장소 검색/추가/삭제/순서변경/방문시간수정) 비즈니스 로직을 담당한다."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.clients import tour_api
from app.core.exceptions import AppError, ErrorCode
from app.repositories.place_repository import PlaceRepository
from app.repositories.region_repository import RegionRepository
from app.repositories.trip_place_repository import TripPlaceRepository
from app.repositories.trip_repository import TripRepository
from app.schemas.place import (
    CustomPlaceAddRequest,
    CustomPlaceAddResponse,
    PlaceSearchItem,
    PlaceSearchResponse,
    TripPlaceAddRequest,
    TripPlaceAddResponse,
    TripPlaceOrderUpdateRequest,
    TripPlaceOrderUpdateResponse,
    TripPlaceVisitUpdateRequest,
    TripPlaceVisitUpdateResponse,
)
from app.schemas.user import CurrentUser

# TourAPI 자체 지역코드(서울=1, 부산=6). regions 테이블에는 저장하지 않는다 —
# Issue #1 리뷰에서 "Region 은 공유 테이블이라 ERD(id/name/isSupported) 외
# 컬럼을 추가하지 않는다"고 정리했고, 지원 지역이 2개뿐이라 여기서 상수로
# 관리하는 편이 스키마를 건드리지 않고도 충분하다.
_TOUR_API_AREA_CODES: dict[int, str] = {
    1: "1",  # 서울특별시
    2: "6",  # 부산광역시
}

# 직접 등록 주소가 여행 지역 범위 안에 있는지 판별할 때 쓰는 시/도 접두어.
# TourAPI 지역코드와 달리 이건 사용자가 입력한 실제 주소 문자열과 비교해야 해서,
# regions 테이블의 정식 명칭("서울특별시")이 아니라 주소에 실제로 쓰이는
# 축약형으로 매칭한다.
_REGION_ADDRESS_PREFIXES: dict[int, tuple[str, ...]] = {
    1: ("서울",),  # 서울특별시
    2: ("부산",),  # 부산광역시
}

# 명세서에 정확한 숫자가 없어 "최소 1개는 있어야 한다"는 가장 보수적인 기준으로
# 잠정 구현했다 — 팀 확정 시 이 값만 바꾸면 된다.
_MIN_TRIP_PLACES = 1


class PlaceService:
    """places 라우터가 호출하는 검색/추가 검증·조합 로직을 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.places = PlaceRepository(db)
        self.trip_places = TripPlaceRepository(db)
        self.trips = TripRepository(db)
        self.regions = RegionRepository(db)

    def search_places(self, keyword: str, region_id: int | None) -> PlaceSearchResponse:
        area_code = None
        if region_id is not None:
            if self.regions.get_supported_by_id(region_id) is None:
                raise AppError(
                    ErrorCode.RESOURCE_NOT_FOUND,
                    "선택한 지역을 찾을 수 없습니다.",
                    status_code=404,
                )
            area_code = _TOUR_API_AREA_CODES.get(region_id)

        results = tour_api.search_places(keyword, area_code=area_code)
        items = [self._get_or_create_place(result, region_id) for result in results]
        # get_or_create()/보충 로직이 flush만 하므로, 검색으로 새로 만든/보충한 place가
        # 요청 종료 후에도 남도록 여기서 한 번만 commit한다.
        self.db.commit()
        return PlaceSearchResponse(places=items)

    def _get_or_create_place(self, result: tour_api.TourApiPlace, region_id: int | None) -> PlaceSearchItem:
        place = self.places.get_or_create(
            source_type="tour_api",
            tour_content_id=result.content_id or None,
            region_id=region_id,
            name=result.name,
            longitude=result.longitude,
            latitude=result.latitude,
            area_cd=result.area_cd,
            signgu_cd=result.signgu_cd,
        )
        # 지역코드 보충은 PlaceRepository.get_or_create() 내부(충돌 폴백 경로)에서 이미
        # 처리된다 — STEP3(여기)·STEP6(recommendation/service.py)가 같은 메서드를 거치므로
        # 별도 보충 로직을 여기 다시 두지 않는다.
        return PlaceSearchItem(
            place_id=place.id,
            name=result.name,
            address=result.address,
            latitude=result.latitude,
            longitude=result.longitude,
        )

    def add_place_to_trip(
        self,
        current_user: CurrentUser,
        trip_id: UUID,
        payload: TripPlaceAddRequest,
    ) -> TripPlaceAddResponse:
        trip = self.trips.get_owned_by_id(trip_id, current_user.id)
        if trip is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "여행 일정을 찾을 수 없습니다.",
                status_code=404,
            )

        if self.places.get_by_id(payload.place_id) is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "장소를 찾을 수 없습니다.",
                status_code=404,
            )

        if self.trip_places.exists(trip_id, payload.place_id):
            raise AppError(
                ErrorCode.DUPLICATE_PLACE_ID,
                "이미 등록된 장소입니다.",
                status_code=409,
            )

        position = self.trip_places.next_position(trip_id)
        trip_place = self.trip_places.add(
            trip_id=trip_id,
            place_id=payload.place_id,
            position=position,
            visit_time=payload.visit_time,
        )

        return TripPlaceAddResponse(
            trip_place_id=trip_place.id,
            trip_id=trip_place.trip_id,
            place_id=trip_place.place_id,
            visit_order=trip_place.position,
            visit_time=trip_place.visit_time,
            is_fixed=trip_place.is_fixed,
        )

    def add_custom_place_to_trip(
        self,
        current_user: CurrentUser,
        trip_id: UUID,
        payload: CustomPlaceAddRequest,
    ) -> CustomPlaceAddResponse:
        """검색 결과에 없는 장소를 이름/주소로 직접 등록한다(Figma node 48:3842).

        커스텀 장소는 집중도 분석 대상이 아니므로(is_recommendable=False)
        방문 시간도 검색 결과 등록(add_place_to_trip)과 동일하게 선택 입력이다.
        위경도는 Kakao 지오코딩("카카오맵" 제품 비활성화로 당장 못 씀)이 가능해지면
        나중에 배치로 채우기로 하고, 지금은 주소 원문만 텍스트로 저장한다(Place.address).

        경험태그(분류) 선택은 받지 않는다 — is_recommendable=False 라 추천 후보
        조회에서 애초에 제외되어 저장해도 쓰이지 않았고, STEP3 완료 직후
        "방문 목적" 화면(TripPurposeForm)에서 같은 태그 목록을 다시 물어봐서
        중복 입력으로만 느껴졌다.
        """
        trip = self.trips.get_owned_by_id(trip_id, current_user.id)
        if trip is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "여행 일정을 찾을 수 없습니다.",
                status_code=404,
            )

        prefixes = _REGION_ADDRESS_PREFIXES.get(trip.region_id)
        if prefixes and not payload.address.strip().startswith(prefixes):
            raise AppError(
                ErrorCode.ADDRESS_NOT_FOUND,
                f"{trip.region.name} 지역 내 주소만 등록할 수 있어요.",
                status_code=400,
            )

        place = self.places.create(
            source_type="custom",
            tour_content_id=None,
            region_id=trip.region_id,
            name=payload.name,
            longitude=None,
            latitude=None,
            is_recommendable=False,
            address=payload.address,
        )

        position = self.trip_places.next_position(trip_id)
        trip_place = self.trip_places.add(
            trip_id=trip_id,
            place_id=place.id,
            position=position,
            visit_time=payload.visit_time,
        )

        return CustomPlaceAddResponse(
            trip_place_id=trip_place.id,
            trip_id=trip_place.trip_id,
            place_id=place.id,
            visit_order=trip_place.position,
            visit_time=trip_place.visit_time,
            is_fixed=trip_place.is_fixed,
            name=place.name,
        )

    def remove_place_from_trip(self, current_user: CurrentUser, trip_place_id: UUID) -> None:
        trip_place = self.trip_places.get_owned_by_id(trip_place_id, current_user.id)
        if trip_place is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "장소를 찾을 수 없습니다.",
                status_code=404,
            )

        current_count = self.trip_places.count_by_trip(trip_place.trip_id)
        remaining_count = current_count - 1
        if remaining_count < _MIN_TRIP_PLACES:
            raise AppError(
                ErrorCode.MINIMUM_PLACES_REQUIRED,
                f"일정에는 최소 {_MIN_TRIP_PLACES}개 이상의 장소가 있어야 합니다.",
                status_code=409,
                extra={"remainingCount": remaining_count},
            )

        self.trip_places.delete(trip_place)

    def reorder_places(
        self,
        current_user: CurrentUser,
        trip_id: UUID,
        payload: TripPlaceOrderUpdateRequest,
    ) -> TripPlaceOrderUpdateResponse:
        trip = self.trips.get_owned_by_id(trip_id, current_user.id)
        if trip is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "여행 일정을 찾을 수 없습니다.",
                status_code=404,
            )

        requested_ids = [item.trip_place_id for item in payload.order]
        owned = self.trip_places.get_owned_by_ids(trip_id, requested_ids, current_user.id)
        if len(owned) != len(requested_ids):
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "이 여행에 등록되지 않은 장소가 포함되어 있습니다.",
                status_code=404,
            )

        positions = {item.trip_place_id: item.visit_order for item in payload.order}
        self.trip_places.reorder(positions)

        # 순서가 바뀌면 경로/이동시간이 전부 달라지므로 무조건 재분석이 필요하다.
        trip = self.trips.mark_needs_reanalysis(trip)

        return TripPlaceOrderUpdateResponse(
            trip_id=trip.id,
            needs_reanalysis=trip.needs_reanalysis,
            updated_at=trip.updated_at,
        )

    def update_trip_place_visit(
        self,
        current_user: CurrentUser,
        trip_place_id: UUID,
        payload: TripPlaceVisitUpdateRequest,
    ) -> TripPlaceVisitUpdateResponse:
        trip_place = self.trip_places.get_owned_by_id(trip_place_id, current_user.id)
        if trip_place is None:
            raise AppError(
                ErrorCode.RESOURCE_NOT_FOUND,
                "장소를 찾을 수 없습니다.",
                status_code=404,
            )

        fields = payload.model_dump(exclude_unset=True)
        trip_place = self.trip_places.update_visit(
            trip_place,
            visit_time=payload.visit_time,
            duration_minutes=payload.duration_minutes,
            is_fixed=payload.is_fixed,
            fields=fields,
        )

        return TripPlaceVisitUpdateResponse(
            trip_place_id=trip_place.id,
            visit_time=trip_place.visit_time,
            duration_minutes=trip_place.stay_minutes,
            is_fixed=trip_place.is_fixed,
            # 방문시간·체류시간·고정여부 수정은 needsReanalysis 를 바꾸지 않는다.
            needs_reanalysis=trip_place.trip.needs_reanalysis,
            updated_at=trip_place.updated_at,
        )
