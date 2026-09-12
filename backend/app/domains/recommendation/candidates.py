"""STEP6 대안 후보 탐색 파이프라인.

generate -> enrich(집중도 판정) -> filter(hard filter) -> score(experience_score) 순.
경로 점수/이유/랭킹(총점)은 다루지 않는다 — 그건 route-scores 엔드포인트(Part3)의 몫이다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

from app.clients.tour_api import TourPlaceItem, fetch_nearby_places
from app.domains.analysis.service import (
    ConcentrationLevel,
    MappingStatus,
    calculate_congestion_level,
    get_spots_and_items_for_codes,
    match_concentration_spot,
)
from app.repositories.analysis_repository import AnalysisRepository

# 자동으로 확대되는 반경 단계(km). relaxed_experience는 사용자가 직접 선택했을 때만 쓴다.
RADIUS_KM_BY_MODE = {
    "default": 3.0,
    "expanded_radius": 5.0,
    "relaxed_experience": 5.0,
}
MIN_CANDIDATES = 3
MAX_CANDIDATES = 5
DEFAULT_EXPERIENCE_THRESHOLD = 0.3
RELAXED_EXPERIENCE_THRESHOLD = 0.15


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# place_experience_tag 실측 데이터가 아직 얇은 동안 쓰는 카테고리 기반 대체 가중치.
# TourAPI locationBasedList2가 실제로 돌려주는 cat2(중분류) 코드를 experience_tag.code로
# 매핑한다(2026-09 categoryCode2 실측 기준). 후보에 이 가중치로 place_experience_tag를
# source="tour_category"로 채워 넣으면, 이후에는 이 표 대신 실제 테이블을 조회하게 된다.
CATEGORY_TAG_WEIGHTS: dict[str, dict[str, float]] = {
    "A0101": {"nature_walk": 1.0},                                    # 자연관광지
    "A0102": {"nature_walk": 0.6},                                    # 관광자원
    "A0201": {"history_culture": 1.0},                                # 역사관광지
    "A0202": {"nature_walk": 0.6, "cafe_rest": 0.4},                  # 휴양관광지
    "A0203": {"activity_experience": 1.0},                            # 체험관광지
    "A0204": {"activity_experience": 0.6, "exhibit_performance": 0.4},  # 산업관광지
    "A0205": {"architecture_space": 1.0, "photo_view": 0.5},          # 건축/조형물
    "A0206": {"exhibit_performance": 1.0},                            # 문화시설
    "A0207": {"exhibit_performance": 0.8},                            # 축제
    "A0208": {"exhibit_performance": 0.8},                            # 공연/행사
    "A0301": {"activity_experience": 0.8},                           # 레포츠소개
    "A0302": {"activity_experience": 1.0},                           # 육상 레포츠
    "A0303": {"activity_experience": 1.0},                           # 수상 레포츠
    "A0304": {"activity_experience": 1.0},                           # 항공 레포츠
    "A0305": {"activity_experience": 1.0},                           # 복합 레포츠
    "A0401": {"food_market": 0.5},                                   # 쇼핑
    "A0502": {"food_market": 1.0},                                   # 음식점
}

CATEGORY_LABELS: dict[str, str] = {
    "A0101": "자연관광지", "A0102": "관광자원", "A0201": "역사관광지", "A0202": "휴양관광지",
    "A0203": "체험관광지", "A0204": "산업관광지", "A0205": "건축/조형물", "A0206": "문화시설",
    "A0207": "축제", "A0208": "공연/행사", "A0301": "레포츠소개", "A0302": "육상 레포츠",
    "A0303": "수상 레포츠", "A0304": "항공 레포츠", "A0305": "복합 레포츠", "A0401": "쇼핑",
    "A0502": "음식점",
}

# cat2 체계에 정확히 대응하는 대분류가 없는 태그를 보완하는 이름 키워드 매칭.
# 카테고리 매핑과 같이 써서 실측 데이터가 붙기 전까지 experience_score 정확도를 보완한다.
EXPERIENCE_TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "nature_walk": ("공원", "산", "숲", "둘레길", "강", "호수", "정원", "동산", "생태"),
    # 바로 "궁" 한 글자는 "무궁화" 같은 무관한 단어에도 걸려서(실측으로 발견) 빼고
    # 실제 궁궐명을 구체적으로 나열한다 — 그 외 역사 유적은 카테고리 매핑(A0201)이 이미 잡아준다.
    "history_culture": (
        "경복궁", "창덕궁", "덕수궁", "창경궁", "경희궁", "종묘",
        "역사", "문화재", "유적", "사찰", "향교", "서원", "고택",
    ),
    "architecture_space": ("타워", "건축", "빌딩", "광장", "다리", "한옥"),
    "photo_view": ("전망", "뷰", "포토", "야경"),
    "food_market": ("시장", "먹거리", "맛집", "골목"),
    "cafe_rest": ("카페", "베이커리", "찻집", "휴게"),
    "activity_experience": ("체험", "공방", "테마파크", "레포츠"),
    "exhibit_performance": ("박물관", "미술관", "전시", "공연장", "갤러리", "기념관"),
    "family_activity": ("어린이", "키즈", "동물원", "놀이"),
}


def category_label(category_code: str | None) -> str | None:
    if category_code is None:
        return None
    return CATEGORY_LABELS.get(category_code)


def derive_tag_code_weights(candidate_name: str, category_code: str | None) -> dict[str, float]:
    """카테고리 코드(있으면) + 이름 키워드로 후보의 experience_tag.code별 가중치를 추정한다."""
    weights: dict[str, float] = {}
    if category_code and category_code in CATEGORY_TAG_WEIGHTS:
        weights.update(CATEGORY_TAG_WEIGHTS[category_code])
    for code, keywords in EXPERIENCE_TAG_KEYWORDS.items():
        if any(keyword in candidate_name for keyword in keywords):
            weights[code] = max(weights.get(code, 0.0), 0.7)
    return weights


def category_only_tag_weights(category_code: str | None) -> dict[str, float]:
    """place_experience_tag(source=tour_category)로 영구 저장할 값 — 카테고리 근거만 쓴다.

    이름 키워드 매칭은 experience_score 계산 보조용 추정치라 실측 데이터로 저장하기엔
    근거가 약해서 뺀다.
    """
    if category_code and category_code in CATEGORY_TAG_WEIGHTS:
        return dict(CATEGORY_TAG_WEIGHTS[category_code])
    return {}


SCORE_NO_PURPOSE_SELECTED = 0.5  # 목적을 선택하지 않음 — 판단 근거 자체가 없어 중립값
SCORE_NO_EVIDENCE = 0.2  # 카테고리/키워드 근거가 전혀 없음("정보 부족") — 불일치와는 구분한다
SCORE_NO_OVERLAP = 0.05  # 근거는 있으나 선택한 목적과 전혀 안 겹침("명확한 불일치")


def mock_experience_score(
    candidate_name: str, category_code: str | None, purpose_tag_codes: list[str]
) -> float:
    """선택한 방문 목적 태그와 후보의 추정 태그 가중치를 비교해 experience_score를 매긴다.

    "정보 부족"(카테고리/키워드 근거가 없음)과 "불일치"(근거는 있지만 선택한 목적과 안 겹침)를
    점수로 구분해야 hard filter(<DEFAULT_EXPERIENCE_THRESHOLD)와 relaxed_experience 모드가
    실제로 다른 후보 집합을 걸러낸다. 이전 버전은 두 경우 모두 threshold(0.3) 이상으로
    바닥값을 줘서 필터가 사실상 아무것도 걸러내지 못했다(후보 무관 candidate_id 기반 변주만 있었음).
    """
    if not purpose_tag_codes:
        return SCORE_NO_PURPOSE_SELECTED

    weights = derive_tag_code_weights(candidate_name, category_code)
    if not weights:
        return SCORE_NO_EVIDENCE

    matched = [weights.get(code, 0.0) for code in purpose_tag_codes]
    avg = sum(matched) / len(matched)
    if avg <= 0:
        return SCORE_NO_OVERLAP
    return round(0.35 + avg * 0.65, 4)


@dataclass
class CandidateSource:
    """TourAPI 후보와 DB 후보 풀을 같은 모양으로 다루기 위한 공용 표현."""
    id: str  # place_id(DB 후보) 또는 tour_content_id(TourAPI 후보)
    name: str
    latitude: float
    longitude: float
    area_cd: str | None = None
    signgu_cd: str | None = None
    category_code: str | None = None
    from_tour_api: bool = False


@dataclass
class EnrichedCandidate:
    source: CandidateSource
    congestion_level: str
    experience_score: float
    category_weights: dict[str, float] = field(default_factory=dict)


def generate_candidates(
    origin_lat: float,
    origin_lng: float,
    radius_km: float,
    db_pool_fetcher,
) -> list[CandidateSource]:
    """TourAPI 위치기반 후보를 우선 쓰고, 키가 없거나 응답이 비면 DB 후보 풀로 대체한다.

    db_pool_fetcher(radius_m) -> list[dict(id,name,lat,lng,tour_content_id)] 를 주입받아
    repository 의존을 이 모듈 밖으로 뺀다(순수 함수 유지).
    """
    tour_items: list[TourPlaceItem] = fetch_nearby_places(origin_lat, origin_lng, round(radius_km * 1000))
    if tour_items:
        return [
            CandidateSource(
                id=item.content_id,
                name=item.name,
                latitude=item.latitude,
                longitude=item.longitude,
                area_cd=item.area_cd,
                signgu_cd=item.signgu_cd,
                category_code=item.category_code,
                from_tour_api=True,
            )
            for item in tour_items
        ]

    pool = db_pool_fetcher(radius_km * 1000)
    return [
        CandidateSource(
            id=str(row["id"]),
            name=row["name"],
            latitude=row["lat"],
            longitude=row["lng"],
            area_cd=row.get("area_cd"),
            signgu_cd=row.get("signgu_cd"),
        )
        for row in pool
    ]


def enrich_candidates(
    candidates: list[CandidateSource],
    travel_date: date | None,
    purpose_tag_codes: list[str],
    analysis_repo: AnalysisRepository,
) -> list[EnrichedCandidate]:
    """집중률 매핑/판정을 후보에도 재사용해서 congestion_level을 채운다.

    area_cd/signgu_cd는 TourAPI 응답(lDongRegnCd/lDongSignguCd)에서 이미 채워져 있으므로
    STEP4처럼 trip.region_id -> region 매핑을 다시 거치지 않는다. DB 후보 풀 항목은
    지역 코드가 없어(place에 region_id가 비어 있을 수 있음) congestion_level="unknown"으로 둔다.
    """
    enriched: list[EnrichedCandidate] = []
    region_cache: dict[tuple[str, str], tuple] = {}
    for candidate in candidates:
        if candidate.area_cd and candidate.signgu_cd:
            cache_key = (candidate.area_cd, candidate.signgu_cd)
            if cache_key not in region_cache:
                region_cache[cache_key] = get_spots_and_items_for_codes(
                    analysis_repo, candidate.area_cd, candidate.signgu_cd, travel_date
                )
            spots, items_by_name, api_failed = region_cache[cache_key]
        else:
            spots, items_by_name, api_failed = [], {}, False

        if api_failed or not spots:
            level = "unknown"
        else:
            match = match_concentration_spot(candidate.name, spots)
            # STEP4와 같은 기준: review_required(검수 대기)는 아직 확정된 매핑이 아니므로
            # 확정값처럼 congestion_level을 매기면 안 된다.
            if match.spot is None or match.status == MappingStatus.REVIEW_REQUIRED:
                level = "unknown"
            else:
                item = items_by_name.get(match.spot.tourist_name)
                if item is None or item.raw_value is None:
                    level = "unknown"
                else:
                    level = calculate_congestion_level(item.raw_value)

        enriched.append(
            EnrichedCandidate(
                source=candidate,
                congestion_level=level,
                experience_score=mock_experience_score(
                    candidate.name, candidate.category_code, purpose_tag_codes
                ),
                category_weights=category_only_tag_weights(candidate.category_code),
            )
        )
    return enriched


def filter_candidates(
    enriched: list[EnrichedCandidate],
    duplicate_names: set[str],
    experience_threshold: float,
) -> tuple[list[EnrichedCandidate], int]:
    """hard filter: duplicate_place / high_concentration / low_experience_score.

    operation_closed는 운영시간 데이터가 없어 걸러지지 않는다(TODO).
    """
    survivors = []
    excluded = 0
    for candidate in enriched:
        if candidate.source.name in duplicate_names:
            excluded += 1
            continue
        if candidate.congestion_level == ConcentrationLevel.HIGH:
            excluded += 1
            continue
        if candidate.experience_score < experience_threshold:
            excluded += 1
            continue
        survivors.append(candidate)
    return survivors, excluded


def select_top_candidates(
    survivors: list[EnrichedCandidate], limit: int
) -> list[EnrichedCandidate]:
    """요청에 담을 후보를 experience_score 기준 상위 limit개로 뽑는다.

    generate_candidates가 돌려주는 순서는 TourAPI의 거리순(arrange=E)이라, 정렬 없이 그냥
    앞에서부터 자르면 거리는 가깝지만 목적과 안 맞는 후보가 살아남고 더 적합한 후보가 밀려날
    수 있다. congestion_level은 이미 filter_candidates에서 high가 걸러진 뒤라 나머지는
    experience_score만으로 우선순위를 매긴다.
    """
    return sorted(survivors, key=lambda c: c.experience_score, reverse=True)[:limit]
