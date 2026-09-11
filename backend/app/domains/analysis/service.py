"""STEP4 집중도 분석 비즈니스 로직.

trip.region_id -> region.area_cd/signgu_cd 로 집중률 API(area_cd/signgu_cd 단위)를 호출한다.
region에 코드가 아직 없으면(매핑 전) 지역 전체를 "region_not_supported"로 안전하게 처리한다.
"""
from __future__ import annotations

import difflib
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.clients.concentration_api import ConcentrationApiError, ConcentrationItem, fetch_concentration
from app.core.exceptions import AppError, ErrorCode
from app.db.models.concentration import ConcentrationSpot, PlaceConcentrationMapping
from app.db.models.trip_place import TripPlace
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.user import CurrentUser

logger = logging.getLogger("yeogimalgo.analysis")


class AnalysisStatus:
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class ConcentrationLevel:
    LOW = "low"
    MID = "mid"
    HIGH = "high"


class UnknownReason:
    REGION_NOT_SUPPORTED = "region_not_supported"
    NO_MAPPING = "no_mapping"
    MAPPING_PENDING = "mapping_pending"
    NO_FORECAST_DATA = "no_forecast_data"


class MappingStatus:
    AUTO_APPROVED = "auto_approved"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"


RULE_VERSION = "v1"
# 실측 결과(2026-09-07, concentration_api_test.py --collect): 서울 종로구/중구/마포구,
# 6000건 표본, 200개 관광지의 향후 30일 cnctrRate 3분위수. 기준이 바뀌면 v2로 올리고
# 과거 분석 결과(rule_version="v1")는 그대로 보존한다.
_LOW_CUTOFF = 62.23
_MID_CUTOFF = 81.39

_FUZZY_THRESHOLD = 0.8
_SUFFIX_PATTERN = re.compile(r"(관광지|공원)$")
_PAREN_PATTERN = re.compile(r"\([^)]*\)")


def calculate_congestion_level(raw_value: float, rule_version: str = RULE_VERSION) -> str:
    """cnctrRate 원본 수치를 low/mid/high로 변환한다(임시 컷오프, rule_version으로 버전 관리)."""
    if raw_value <= _LOW_CUTOFF:
        return ConcentrationLevel.LOW
    if raw_value <= _MID_CUTOFF:
        return ConcentrationLevel.MID
    return ConcentrationLevel.HIGH


def normalize_name(name: str) -> str:
    """정규화 범위: 유니코드 정규화, 공백 정규화, 괄호 속 부가명 제거, 접미어 통일."""
    value = unicodedata.normalize("NFKC", name)
    value = _PAREN_PATTERN.sub("", value)
    value = re.sub(r"\s+", "", value)
    value = _SUFFIX_PATTERN.sub("", value)
    return value.strip()


@dataclass
class MatchResult:
    spot: ConcentrationSpot | None
    match_method: str | None
    confidence: Decimal | None
    status: str


def match_concentration_spot(place_name: str, spots: list[ConcentrationSpot]) -> MatchResult:
    """exact/normalized/fuzzy 단계로 관광지명을 매칭한다. alias 사전은 아직 없어 생략(TODO)."""
    if not spots:
        return MatchResult(None, None, None, "no_mapping")

    normalized_target = normalize_name(place_name)

    exact_matches = [s for s in spots if s.tourist_name == place_name]
    if len(exact_matches) == 1:
        return MatchResult(exact_matches[0], "exact", Decimal("1.0"), MappingStatus.AUTO_APPROVED)
    if len(exact_matches) > 1:
        return MatchResult(exact_matches[0], "exact", Decimal("1.0"), MappingStatus.REVIEW_REQUIRED)

    normalized_matches = [s for s in spots if s.normalized_name == normalized_target]
    if len(normalized_matches) == 1:
        return MatchResult(
            normalized_matches[0], "normalized", Decimal("1.0"), MappingStatus.AUTO_APPROVED
        )
    if len(normalized_matches) > 1:
        return MatchResult(
            normalized_matches[0], "normalized", Decimal("1.0"), MappingStatus.REVIEW_REQUIRED
        )

    best_spot: ConcentrationSpot | None = None
    best_ratio = 0.0
    for spot in spots:
        ratio = difflib.SequenceMatcher(None, normalized_target, spot.normalized_name).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_spot = spot

    if best_spot is not None and best_ratio >= _FUZZY_THRESHOLD:
        return MatchResult(
            best_spot, "fuzzy", Decimal(str(round(best_ratio, 4))), MappingStatus.REVIEW_REQUIRED
        )

    return MatchResult(None, None, None, "no_mapping")


def _select_items_for_date(
    api_items: list[ConcentrationItem], travel_date: date | None
) -> dict[str, ConcentrationItem]:
    """관광지명별로 baseYmd가 travel_date와 일치하는 항목 하나를 고른다.

    한 번 호출로 향후 30일치가 모두 오므로, travel_date를 안 걸러주면 "마지막으로 처리된
    날짜"가 임의로 골라지는 버그가 생긴다. travel_date가 없으면 가장 이른 예측일을 쓴다.
    """
    target = travel_date.strftime("%Y%m%d") if travel_date else None
    by_name: dict[str, ConcentrationItem] = {}
    for item in api_items:
        if target is not None:
            if item.base_ymd == target:
                by_name[item.tourist_name] = item
            continue
        existing = by_name.get(item.tourist_name)
        if existing is None or item.base_ymd < existing.base_ymd:
            by_name[item.tourist_name] = item
    return by_name


def get_spots_and_items_for_codes(
    repo: AnalysisRepository, area_cd: str, signgu_cd: str, travel_date: date | None = None
) -> tuple[list[ConcentrationSpot], dict[str, ConcentrationItem], bool]:
    """area_cd/signgu_cd를 직접 받아 집중률 API를 호출하고 spot 목록·item 매핑을 돌려준다.

    STEP4(run_analysis)와 STEP6(candidate 보강)이 같은 판정 기준을 쓰도록 이 함수와
    match_concentration_spot/calculate_congestion_level을 그대로 재사용한다.
    반환값의 마지막 bool은 API 호출 자체가 실패했는지 여부다.
    """
    try:
        api_items = fetch_concentration(area_cd, signgu_cd)
    except ConcentrationApiError as exc:
        logger.warning("집중률 API 호출 실패(area=%s, signgu=%s): %s", area_cd, signgu_cd, exc)
        return [], {}, True

    for item in api_items:
        repo.get_or_create_spot(
            area_cd=item.area_cd,
            signgu_cd=item.signgu_cd,
            tourist_name=item.tourist_name,
            normalized_name=normalize_name(item.tourist_name),
        )
    spots = repo.list_spots_by_region(area_cd, signgu_cd)
    items_by_name = _select_items_for_date(api_items, travel_date)
    return spots, items_by_name, False


def get_region_spots_and_items(
    repo: AnalysisRepository, region_id: int | None, travel_date: date | None = None
) -> tuple[list[ConcentrationSpot], dict[str, ConcentrationItem], bool]:
    """trip.region_id -> region.area_cd/signgu_cd 로 get_spots_and_items_for_codes를 호출한다."""
    region = repo.get_region(region_id)
    if region is None or not region.area_cd or not region.signgu_cd:
        return [], {}, False
    return get_spots_and_items_for_codes(repo, region.area_cd, region.signgu_cd, travel_date)


class AnalysisService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = AnalysisRepository(db)

    def _get_trip_or_404(self, trip_id: UUID, user: CurrentUser):
        trip = self.repo.get_trip_owned(trip_id, user.id)
        if trip is None:
            raise AppError(ErrorCode.RESOURCE_NOT_FOUND, "일정을 찾을 수 없습니다.", status_code=404)
        return trip

    def run_analysis(self, user: CurrentUser, trip_id: UUID) -> dict:
        trip = self._get_trip_or_404(trip_id, user)
        if not trip.places:
            raise AppError(
                ErrorCode.NO_PLACES_IN_TRIP, "일정에 등록된 장소가 없습니다.", status_code=422
            )

        places_map = self.repo.get_places_map([p.place_id for p in trip.places])
        region = self.repo.get_region(trip.region_id)
        region_supported = region is not None and region.area_cd and region.signgu_cd
        spots, items_by_name, api_failed = get_region_spots_and_items(
            self.repo, trip.region_id, trip.travel_date
        )

        try:
            for trip_place in trip.places:
                place = places_map.get(trip_place.place_id)
                place_name = place.name if place else ""
                self._analyze_place(
                    trip_place, place_name, region_supported, api_failed, spots, items_by_name
                )
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AppError(
                ErrorCode.DB_ERROR, "분석 결과를 저장하는 중 오류가 발생했습니다.", status_code=500
            ) from exc

        return self.get_analysis(user, trip_id, status_filter=None)

    def _analyze_place(
        self,
        trip_place: TripPlace,
        place_name: str,
        region_supported: bool,
        api_failed: bool,
        spots: list[ConcentrationSpot],
        items_by_name: dict[str, ConcentrationItem],
    ) -> None:
        if not region_supported:
            self.repo.upsert_mapping(trip_place.place_id, None, None, None, "no_mapping")
            self.repo.upsert_analysis(
                trip_place.id,
                AnalysisStatus.UNAVAILABLE,
                None,
                UnknownReason.REGION_NOT_SUPPORTED,
                RULE_VERSION,
            )
            return

        if api_failed:
            self.repo.upsert_analysis(trip_place.id, AnalysisStatus.FAILED, None, None, None)
            return

        existing = self.repo.get_mapping(trip_place.place_id)
        if existing is not None and existing.status in (MappingStatus.APPROVED, MappingStatus.REJECTED):
            # 사람이 이미 확정한 매핑이 있으면 자동 재매칭을 하지 않고 그 결과를 그대로 쓴다.
            self._apply_reviewed_mapping(trip_place, existing, items_by_name)
            return

        match = match_concentration_spot(place_name, spots)
        if match.spot is None:
            self.repo.upsert_mapping(trip_place.place_id, None, None, None, "no_mapping")
            self.repo.upsert_analysis(
                trip_place.id, AnalysisStatus.UNAVAILABLE, None, UnknownReason.NO_MAPPING, RULE_VERSION
            )
            return

        self.repo.upsert_mapping(
            trip_place.place_id, match.spot.id, match.match_method, match.confidence, match.status
        )

        if match.status == MappingStatus.REVIEW_REQUIRED:
            self.repo.upsert_analysis(
                trip_place.id,
                AnalysisStatus.UNAVAILABLE,
                None,
                UnknownReason.MAPPING_PENDING,
                RULE_VERSION,
            )
            return

        item = items_by_name.get(match.spot.tourist_name)
        if item is None or item.raw_value is None:
            self.repo.upsert_analysis(
                trip_place.id,
                AnalysisStatus.UNAVAILABLE,
                None,
                UnknownReason.NO_FORECAST_DATA,
                RULE_VERSION,
            )
            return

        level = calculate_congestion_level(item.raw_value, RULE_VERSION)
        self.repo.upsert_analysis(trip_place.id, AnalysisStatus.SUCCESS, level, None, RULE_VERSION)

    def _apply_reviewed_mapping(
        self,
        trip_place: TripPlace,
        mapping: PlaceConcentrationMapping,
        items_by_name: dict[str, ConcentrationItem],
    ) -> None:
        if mapping.status == MappingStatus.REJECTED or mapping.concentration_spot_id is None:
            self.repo.upsert_analysis(
                trip_place.id, AnalysisStatus.UNAVAILABLE, None, UnknownReason.NO_MAPPING, RULE_VERSION
            )
            return

        spot = self.repo.get_spot(mapping.concentration_spot_id)
        if spot is None:
            self.repo.upsert_analysis(
                trip_place.id, AnalysisStatus.UNAVAILABLE, None, UnknownReason.NO_MAPPING, RULE_VERSION
            )
            return

        item = items_by_name.get(spot.tourist_name)
        if item is None or item.raw_value is None:
            self.repo.upsert_analysis(
                trip_place.id,
                AnalysisStatus.UNAVAILABLE,
                None,
                UnknownReason.NO_FORECAST_DATA,
                RULE_VERSION,
            )
            return

        level = calculate_congestion_level(item.raw_value, RULE_VERSION)
        self.repo.upsert_analysis(trip_place.id, AnalysisStatus.SUCCESS, level, None, RULE_VERSION)

    def get_analysis(self, user: CurrentUser, trip_id: UUID, status_filter: str | None) -> dict:
        trip = self._get_trip_or_404(trip_id, user)
        places = trip.places or []
        places_map = self.repo.get_places_map([p.place_id for p in places])
        analysis_map = self.repo.get_analysis_map([p.id for p in places])

        items: list[dict] = []
        high_count = 0
        for trip_place in places:
            place = places_map.get(trip_place.place_id)
            analysis = analysis_map.get(trip_place.id)
            level = analysis.level if analysis else None
            analysis_status = analysis.analysis_status if analysis else AnalysisStatus.UNAVAILABLE
            unknown_reason = analysis.unknown_reason if analysis else UnknownReason.REGION_NOT_SUPPORTED
            rule_version = analysis.rule_version if analysis else None

            if level == ConcentrationLevel.HIGH:
                high_count += 1

            is_crowded = (
                level == ConcentrationLevel.HIGH
                and trip_place.resolution_status == "pending"
                and not trip_place.is_fixed
            )
            if status_filter == "CROWDED" and not is_crowded:
                continue

            items.append(
                {
                    "tripPlaceId": str(trip_place.id),
                    "placeId": str(trip_place.place_id),
                    "placeName": place.name if place else "",
                    "analysisStatus": analysis_status,
                    "level": level,
                    "unknownReason": unknown_reason,
                    "ruleVersion": rule_version,
                    "isFixed": trip_place.is_fixed,
                    "resolutionStatus": trip_place.resolution_status,
                    "canRecommendAlternative": not trip_place.is_fixed,
                    "analyzedAt": analysis.analyzed_at.isoformat() if analysis and analysis.analyzed_at else None,
                    "visitTime": trip_place.visit_time.strftime("%H:%M") if trip_place.visit_time else None,
                }
            )

        return {
            "tripId": str(trip_id),
            "highConcentrationCount": high_count,
            "items": items,
        }
