"""STEP4 집중도 분석 비즈니스 로직.

trip 전체가 아니라 place 하나하나가 가진 area_cd/signgu_cd(TourAPI lDongRegnCd/lDongSignguCd
기준, place.area_cd/signgu_cd)로 집중률 API를 호출한다 — region.area_cd/signgu_cd 컬럼은
스키마에 남아 있지만(tests/db/test_models.py 기준), region이 시/도 단위(서울특별시/
부산광역시)로 시드돼 있어 구 단위 코드를 의미 있게 담을 수 없다. 그래서 이 도메인은 그
컬럼을 읽지 않고 place 쪽 값만 쓴다. 같은 지역코드는 한 번의 분석 요청 안에서만 캐시하고
요청이 끝나면 버린다. 지역코드가 없는 place는 그 장소 하나만 분석 불가로 처리하고 일정
전체를 막지 않는다.
"""
from __future__ import annotations

import difflib
import logging
import re
import time
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
    NO_DISTRICT_CODE = "no_district_code"
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


def resolve_reviewed_mapping(
    mapping: PlaceConcentrationMapping,
    spot: ConcentrationSpot | None,
    items_by_name: dict[str, ConcentrationItem],
    area_cd: str | None,
    signgu_cd: str | None,
) -> tuple[str | None, str | None]:
    """사람이 승인/거절한 매핑을 그대로 신뢰해 등급을 계산한다 — 순수 함수(DB 접근 없음).

    STEP4(AnalysisService._apply_reviewed_mapping, 분석 결과를 저장)와 STEP6
    (candidates.py::enrich_candidates, 후보 congestion_level만 계산)이 같은 판정 규칙을
    쓰도록 공유한다. 반환값: (level, unknown_reason) — 등급을 낼 수 있으면
    (level, None), 없으면 (None, 그 사유).
    """
    if mapping.status == MappingStatus.REJECTED or mapping.concentration_spot_id is None:
        return None, UnknownReason.NO_MAPPING
    if spot is None:
        return None, UnknownReason.NO_MAPPING
    if spot.area_cd != area_cd or spot.signgu_cd != signgu_cd:
        # 승인된 매핑이 가리키는 spot의 구와 조회 대상 구가 다르다 — 사람이 승인할 당시부터
        # 잘못 매칭했거나, place 지역코드가 애플리케이션 코드를 거치지 않고 바뀐 경우다.
        # 승인/거절 기록 자체는 건드리지 않고 이 판정만 재검수 필요로 표시한다 — 동명이인
        # 관광지의 다른 지역 값을 정상 결과처럼 보여주는 걸 막는다.
        return None, UnknownReason.MAPPING_PENDING
    item = items_by_name.get(spot.tourist_name)
    if item is None or item.raw_value is None:
        return None, UnknownReason.NO_FORECAST_DATA
    return calculate_congestion_level(item.raw_value, RULE_VERSION), None


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
    t0 = time.monotonic()
    try:
        api_items = fetch_concentration(area_cd, signgu_cd)
    except ConcentrationApiError as exc:
        logger.warning("집중률 API 호출 실패(area=%s, signgu=%s): %s", area_cd, signgu_cd, exc)
        return [], {}, True
    logger.info(
        "집중률 API 조회 완료(area=%s signgu=%s): %d건, %.2fs",
        area_cd, signgu_cd, len(api_items), time.monotonic() - t0,
    )

    # 관광지명 기준으로 dedup해서 저장 대상을 만든다(같은 관광지가 최대 30일치 중복으로 온다).
    # 응답 item의 지역코드가 요청과 다르면(드물지만 있을 수 있는 API 응답 이상) 그 항목 하나만
    # 조용히 걸러내지 않고 이 시군구 조회 전체를 실패로 처리한다 — 현재 지역에 동명 관광지가
    # 이미 저장돼 있으면 다른 지역 값이 섞여 들어가 엉뚱한 혼잡도가 표시될 수 있어서다.
    unique_spots: dict[str, str] = {}  # tourist_name -> normalized_name
    for item in api_items:
        if item.area_cd != area_cd or item.signgu_cd != signgu_cd:
            logger.warning(
                "집중률 API 응답 지역코드 불일치(요청 area=%s signgu=%s, 응답 area=%s signgu=%s, "
                "관광지=%s) — 이 시군구 조회 전체를 실패로 처리",
                area_cd, signgu_cd, item.area_cd, item.signgu_cd, item.tourist_name,
            )
            return [], {}, True
        unique_spots.setdefault(item.tourist_name, normalize_name(item.tourist_name))

    t1 = time.monotonic()
    spots = repo.bulk_upsert_spots(area_cd, signgu_cd, list(unique_spots.items()))
    logger.info(
        "spot 저장 완료(area=%s signgu=%s): %d종, %.2fs",
        area_cd, signgu_cd, len(unique_spots), time.monotonic() - t1,
    )

    items_by_name = _select_items_for_date(api_items, travel_date)
    return spots, items_by_name, False


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
        t0 = time.monotonic()
        trip = self._get_trip_or_404(trip_id, user)
        if not trip.trip_places:
            raise AppError(
                ErrorCode.NO_PLACES_IN_TRIP, "일정에 등록된 장소가 없습니다.", status_code=422
            )

        places_map = self.repo.get_places_map([p.place_id for p in trip.trip_places])
        # (area_cd, signgu_cd) -> (spots, items_by_name, api_failed). 이 run_analysis 호출
        # 하나 안에서만 존재하고 끝나면 버려진다 — 여러 요청에 걸쳐 재사용하지 않는다.
        region_cache: dict[tuple[str, str], tuple] = {}
        force = bool(getattr(trip, "needs_reanalysis", False))
        analysis_map = {} if force else self.repo.get_analysis_map(
            [p.id for p in trip.trip_places]
        )
        # needs_reanalysis는 모든 장소 분석과 get_analysis()가 끝난 뒤에만 끈다.
        # upsert_analysis/upsert_mapping이 장소마다 commit하므로, 루프 전에 끄면
        # 이후 장소가 실패해도 플래그가 이미 저장된 채로 남는다.

        # get_analysis()(응답 구성)까지 바깥의 하나의 try로 묶어서, 분석 루프가 아니라
        # 응답 구성 단계에서 오류가 나도(예: get_analysis 내부 DB 조회 실패) 실패 시각
        # 로그가 빠짐없이 남게 한다 — 루프만 감싸면 그 뒤 get_analysis() 실패는 로그 없이
        # 그대로 새어나간다.
        try:
            try:
                for trip_place in trip.trip_places:
                    existing = analysis_map.get(trip_place.id)
                    if (
                        not force
                        and existing is not None
                        and existing.analysis_status == AnalysisStatus.SUCCESS
                        and existing.level is not None
                    ):
                        continue
                    place = places_map.get(trip_place.place_id)
                    self._analyze_place(trip_place, place, trip.travel_date, region_cache)
            except SQLAlchemyError as exc:
                self.db.rollback()
                raise AppError(
                    ErrorCode.DB_ERROR, "분석 결과를 저장하는 중 오류가 발생했습니다.", status_code=500
                ) from exc

            result = self.get_analysis(user, trip_id, status_filter=None)
            if force:
                trip.needs_reanalysis = False
                self.db.commit()
        except Exception:
            logger.error(
                "run_analysis 실패(trip_id=%s): %.2fs 경과 후 오류", trip_id, time.monotonic() - t0
            )
            raise
        else:
            logger.info(
                "run_analysis 완료(trip_id=%s, 장소 %d개): 응답 구성 포함 총 %.2fs",
                trip_id, len(trip.trip_places), time.monotonic() - t0,
            )
            return result

    def _analyze_place(
        self,
        trip_place: TripPlace,
        place,
        travel_date,
        region_cache: dict[tuple[str, str], tuple],
    ) -> None:
        place_name = place.name if place else ""
        area_cd = place.area_cd if place else None
        signgu_cd = place.signgu_cd if place else None

        if not area_cd or not signgu_cd:
            # 이 장소만 지역코드가 없는 것 — 일정 전체가 아니라 이 장소만 분석 불가 처리한다.
            self.repo.upsert_mapping(trip_place.place_id, None, None, None, "no_mapping")
            self.repo.upsert_analysis(
                trip_place.id,
                AnalysisStatus.UNAVAILABLE,
                None,
                UnknownReason.NO_DISTRICT_CODE,
                RULE_VERSION,
            )
            return

        cache_key = (area_cd, signgu_cd)
        if cache_key not in region_cache:
            region_cache[cache_key] = get_spots_and_items_for_codes(
                self.repo, area_cd, signgu_cd, travel_date
            )
        spots, items_by_name, api_failed = region_cache[cache_key]

        if api_failed:
            self.repo.upsert_analysis(trip_place.id, AnalysisStatus.FAILED, None, None, None)
            return

        existing = self.repo.get_mapping(trip_place.place_id)
        if existing is not None and existing.status in (MappingStatus.APPROVED, MappingStatus.REJECTED):
            # 사람이 이미 확정한 매핑이 있으면 자동 재매칭을 하지 않고 그 결과를 그대로 쓴다.
            self._apply_reviewed_mapping(trip_place, existing, items_by_name, area_cd, signgu_cd)
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
        area_cd: str,
        signgu_cd: str,
    ) -> None:
        spot = (
            self.repo.get_spot(mapping.concentration_spot_id)
            if mapping.concentration_spot_id is not None
            else None
        )
        level, reason = resolve_reviewed_mapping(mapping, spot, items_by_name, area_cd, signgu_cd)
        if level is None:
            self.repo.upsert_analysis(trip_place.id, AnalysisStatus.UNAVAILABLE, None, reason, RULE_VERSION)
        else:
            self.repo.upsert_analysis(trip_place.id, AnalysisStatus.SUCCESS, level, None, RULE_VERSION)

    def get_analysis(self, user: CurrentUser, trip_id: UUID, status_filter: str | None) -> dict:
        trip = self._get_trip_or_404(trip_id, user)
        places = trip.trip_places or []
        replacements_map = self.repo.get_active_replacements_map([p.id for p in places])
        place_ids = [p.place_id for p in places]
        place_ids.extend(r.from_place_id for r in replacements_map.values())
        places_map = self.repo.get_places_map(place_ids)
        analysis_map = self.repo.get_analysis_map([p.id for p in places])

        items: list[dict] = []
        high_count = 0
        for trip_place in places:
            place = places_map.get(trip_place.place_id)
            analysis = analysis_map.get(trip_place.id)
            level = analysis.level if analysis else None
            analysis_status = analysis.analysis_status if analysis else AnalysisStatus.UNAVAILABLE
            # analysis가 없는 건 "아직 분석을 실행한 적이 없다"는 뜻이지 "지역코드가 없다"는
            # 뜻이 아니다 — 실제로 지역코드가 멀쩡한 place도 run_analysis()를 아직 한 번도
            # 안 돌렸으면 여기 걸린다. NO_DISTRICT_CODE로 단정하면 원인 파악을 오히려
            # 헷갈리게 하므로(코드 리뷰로 발견, 2026-09-14) 분석 자체를 안 한 경우는
            # unknown_reason을 비워서 "아직 모름"과 "분석해봤는데 이유가 있어 안 됨"을 구분한다.
            unknown_reason = analysis.unknown_reason if analysis else None
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

            replacement = replacements_map.get(trip_place.id)
            from_place = places_map.get(replacement.from_place_id) if replacement else None
            replaced_from = from_place.name if from_place else None

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
                    "wasReplaced": replaced_from is not None,
                    "replacedFrom": replaced_from,
                }
            )

        return {
            "tripId": str(trip_id),
            "highConcentrationCount": high_count,
            "items": items,
        }
