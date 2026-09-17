"""Trip -> 요약 카드 변환 로직. HomeService(GET /home)와 TripService(GET /trips)가
같은 계산(장소 수/지역명/이어서 할 화면 경로)을 공유하려고 분리했다.

ScheduleSummary(schedule_id)와 TripSummaryResponse(trip_id)는 id 필드명만 다르고
나머지는 동일한 모양이다 — ScheduleSummary 쪽 필드명은 이미 배포된 홈 화면 계약이라
(schemas/home.py 주석 참고) 그대로 두고, 여기서 공통 필드만 한 번만 계산한다.
"""
from app.db.models.trip import Trip
from app.repositories.trip_place_repository import TripPlaceRepository
from app.schemas.home import ScheduleSummary
from app.schemas.trip import TripSummaryResponse


def resume_path(trip: Trip) -> str:
    """일정 카드를 눌렀을 때 이동할 경로.

    확정(완료 포함)된 일정은 가이드북으로, 그 외(작성 중)는 항상 STEP3
    장소 목록 화면으로 보낸다 — 방문목적/분석/혼잡해결 중 어디까지 진행했는지는
    더 세분화할 수 있지만(현재 current_step/status 만으로는 추적 불가, 별도
    조사 필요), STEP3 화면은 등록된 장소를 그대로 보여주고 거기서 다음 단계로
    계속 진행할 수 있어 언제나 안전한 재진입 지점이다.
    """
    if trip.status in ("confirmed", "completed"):
        return f"/trips/{trip.id}/guide"
    return f"/trips/{trip.id}/places"


def _common_fields(trip: Trip, trip_places: TripPlaceRepository) -> dict:
    return dict(
        title=trip.title,
        travel_date=trip.travel_date,
        region_name=trip.region.name if trip.region else "",
        place_count=trip_places.count_by_trip(trip.id),
        status=trip.status,
        resume_url=resume_path(trip),
    )


def build_schedule_summary(trip: Trip, trip_places: TripPlaceRepository) -> ScheduleSummary:
    return ScheduleSummary(schedule_id=trip.id, **_common_fields(trip, trip_places))


def build_trip_summary(trip: Trip, trip_places: TripPlaceRepository) -> TripSummaryResponse:
    return TripSummaryResponse(trip_id=trip.id, **_common_fields(trip, trip_places))
