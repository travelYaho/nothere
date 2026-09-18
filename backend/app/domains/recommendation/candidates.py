"""STEP6 대안 후보 탐색 파이프라인.

generate -> enrich(집중도 판정) -> filter(hard filter) -> score(experience_score) 순.
경로 점수/이유/랭킹(총점)은 다루지 않는다 — 그건 route-scores 엔드포인트(Part3)의 몫이다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from app.clients.tour_api import TourPlaceItem, fetch_nearby_places
from app.domains.analysis.service import (
    ConcentrationLevel,
    MappingStatus,
    calculate_congestion_level,
    get_spots_and_items_for_codes,
    match_concentration_spot,
    resolve_reviewed_mapping,
)
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.place_repository import PlaceRepository

if TYPE_CHECKING:
    from app.repositories.recommendation_repository import RecommendationRepository

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


AUTO_CATEGORY_SOURCE = "tour_category"  # place_experience_tag.source — 자동(카테고리 근거) 저장값


def _keyword_tag_weights(candidate_name: str) -> dict[str, float]:
    """이름 키워드만으로 추정한 가중치 — 카테고리 근거와 분리해서 별도로 둔다.

    카테고리 근거(저장된 값이든 이번 응답의 category_code로 라이브 계산한 값이든)
    위에 항상 똑같이 얹을 수 있어야, 저장 전(첫 요청)과 저장 후(재요청)의 점수가
    카테고리 값이 안 바뀌는 한 같아진다(2026-09-16, 코드 리뷰로 발견 — 카테고리만 저장하고
    키워드는 저장하지 않는 설계라, 저장된 값을 무조건 우선하면 첫 요청에서만 있던 키워드
    보완이 재요청부터 사라져 같은 입력에도 점수가 달라졌었다).
    """
    weights: dict[str, float] = {}
    for code, keywords in EXPERIENCE_TAG_KEYWORDS.items():
        if any(keyword in candidate_name for keyword in keywords):
            weights[code] = 0.7
    return weights


def _merge_category_and_keyword(
    category_weights: dict[str, float], candidate_name: str
) -> dict[str, float]:
    """카테고리 근거 가중치 위에 이름 키워드 보완을 얹는다(둘 다 없으면 빈 dict)."""
    weights = dict(category_weights)
    for code, weight in _keyword_tag_weights(candidate_name).items():
        weights[code] = max(weights.get(code, 0.0), weight)
    return weights


def derive_tag_code_weights(candidate_name: str, category_code: str | None) -> dict[str, float]:
    """카테고리 코드(있으면) + 이름 키워드로 후보의 experience_tag.code별 가중치를 추정한다."""
    return _merge_category_and_keyword(category_only_tag_weights(category_code), candidate_name)


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


def _is_valid_stored_weight(weight: float) -> bool:
    """저장된 가중치가 점수 계산에 그대로 쓸 수 있는 유효한 값인지 확인한다.

    0.0은 "그 경험과 무관함"을 뜻하는 정상적인 저장값이라 유효하지만, NaN/inf나
    범위를 벗어난 값은 데이터 오류로 보고 버린다(해당 태그는 추정값으로 대체됨).
    """
    return math.isfinite(weight) and 0.0 <= weight <= 1.0


def _combine_tag_weights(
    stored_weights: dict[str, float], estimated_weights: dict[str, float]
) -> dict[str, float]:
    """저장된 place_experience_tag 값을 우선하고, 저장되지 않은 태그만 카테고리·키워드
    추정으로 보완한다 — 순수 함수. 같은 태그 코드를 중복 합산하지 않는다(저장값이 있으면
    추정값은 그 코드에서 완전히 무시됨).
    """
    combined = dict(stored_weights)
    for code, weight in estimated_weights.items():
        combined.setdefault(code, weight)
    return combined


def resolve_experience_score(
    candidate_name: str,
    category_code: str | None,
    purpose_tag_codes: list[str],
    stored_weights: dict[str, float] | None = None,
    stored_category_weights: dict[str, float] | None = None,
) -> float:
    """선택한 방문 목적 태그와 후보의 태그 가중치를 비교해 experience_score를 매긴다.

    가중치 우선순위(순수 함수 합성, _combine_tag_weights/_merge_category_and_keyword):
    1. `stored_weights` — source가 "tour_category"(자동 카테고리 저장)가 아닌 저장값. 있으면
       그 태그는 이 값을 그대로 쓰고 절대 안 덮인다. ("사람이 직접 확정"을 실제로 검증하는
       건 아니고, "자동 카테고리 출처가 아닌 저장값은 보수적으로 우선한다"는 정책이다.)
    2. 카테고리 근거 — `stored_category_weights`(source="tour_category"로 저장된 값, 태그별)를
       우선하고, 없는 태그 코드만 이번 candidate.category_code로 라이브 계산한 값으로 채운다
       (`_combine_tag_weights`). 저장이 일부 태그만 이뤄진 상태(예: 카테고리 코드가
       {architecture_space, photo_view} 둘 다 나오는데 DB엔 photo_view만 들어있는 경우)에서
       "저장값이 하나라도 있으면 라이브 계산 전체를 버리는" 방식은 안 된다 — 그러면 DO
       NOTHING으로 나머지 태그(architecture_space)가 나중에 채워지는 순간 그 태그가 이번
       요청부터 갑자기 점수에 반영되어, 같은 입력인데도 저장 시점에 따라 결과가 달라진다
       (2026-09-17, 코드 리뷰로 발견·수정). 그래서 태그 코드 단위로 "저장값 우선, 없는
       코드만 라이브 계산으로 보완"해야 한다.
    3. 위 카테고리 근거 위에 이름 키워드 보완을 항상 얹는다(_merge_category_and_keyword).

    카테고리 값만 DB에 저장하고 키워드는 저장하지 않기 때문에(`category_only_tag_weights`
    문서 참고), 저장된 카테고리 값을 "그대로 최종값"처럼 덮어쓰기 우선순위에 넣으면 안
    된다 — 그러면 처음 요청(키워드 보완 포함)과 재요청(카테고리만, 키워드 없음)의 점수가
    같은 입력인데도 달라진다(2026-09-16, 코드 리뷰로 발견·수정). 그래서 카테고리 저장값은
    "덮어쓰기 우선순위"가 아니라 "카테고리 근거의 출처"로만 쓰고, 키워드는 저장 여부와
    무관하게 매번 같은 규칙으로 다시 얹는다.

    "정보 부족"(근거가 전혀 없음)과 "불일치"(근거는 있지만 선택한 목적과 안 겹침)를
    점수로 구분해야 hard filter(<DEFAULT_EXPERIENCE_THRESHOLD)와 relaxed_experience 모드가
    실제로 다른 후보 집합을 걸러낸다. 이전 버전은 두 경우 모두 threshold(0.3) 이상으로
    바닥값을 줘서 필터가 사실상 아무것도 걸러내지 못했다(후보 무관 candidate_id 기반 변주만 있었음).
    """
    if not purpose_tag_codes:
        return SCORE_NO_PURPOSE_SELECTED

    category_basis = _combine_tag_weights(
        stored_category_weights or {}, category_only_tag_weights(category_code)
    )
    estimated = _merge_category_and_keyword(category_basis, candidate_name)
    weights = _combine_tag_weights(stored_weights or {}, estimated)
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
    address: str | None = None
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
                address=item.address,
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


def _resolve_effective_district(
    candidate_area_cd: str | None,
    candidate_signgu_cd: str | None,
    place_area_cd: str | None,
    place_signgu_cd: str | None,
) -> tuple[str | None, str | None, bool]:
    """이번 응답의 지역코드와 기존 place에 저장된 지역코드 중 실제로 쓸 값을 정한다.

    순수 함수(DB 접근 없음). place.area_cd/signgu_cd는 apply_district_code_backfill()의
    충돌 감지 때문에 한 번 채워지면 다른 값으로 조용히 덮어써지지 않는다 — 즉 나중에
    STEP4가 실제로 쓸 지역코드는 "이번 응답 값"이 아니라 "기존 place에 저장된 값"이다.
    여기서 이번 응답 값만 보고 등급을 계산하면, 이 후보를 실제로 적용한 뒤 STEP4가 보여줄
    값과 지금 STEP6에서 보여준 값이 다른 지역 기준일 수 있다(코드 리뷰로 발견,
    2026-09-15). 반환값: (effective_area_cd, effective_signgu_cd, conflict).

    place_repository._classify_district_code_backfill()과 반드시 같은 충돌 규칙을 써야
    한다 — 필드 단위로 비교한다. 2라운드 리뷰로 발견: 처음엔 "저장된 두 필드 중 하나라도
    없으면 저장값 자체가 없는 것으로 취급"했는데, 이러면 area_cd="11", signgu_cd=None처럼
    "부분 저장" 상태에서 area_cd="11"이라는 실제 저장값이 있는데도 통째로 무시하고 후보의
    area_cd="26"을 그냥 써버렸다 — 저장 단계 백필은 area_cd만으로도 충돌을 잡아서 거부하는데
    (기존 값 유지) STEP6는 그걸 모르고 확정 등급을 냈다.
    """
    if not candidate_area_cd or not candidate_signgu_cd:
        # 이번 응답에 완전한 코드가 없다 — place에 저장된 값이 있으면(부분 저장이어도) 그걸
        # 쓰고, 없으면 지역코드 없음으로 취급한다(호출부가 자연히 unknown 처리).
        return place_area_cd, place_signgu_cd, False
    if place_area_cd and place_area_cd != candidate_area_cd:
        return None, None, True
    if place_signgu_cd and place_signgu_cd != candidate_signgu_cd:
        return None, None, True
    if place_area_cd and place_signgu_cd:
        # 저장된 값이 완전하고 충돌도 없다 — 나중에 STEP4가 실제로 쓸 값(저장값)을 신뢰한다.
        return place_area_cd, place_signgu_cd, False
    return candidate_area_cd, candidate_signgu_cd, False


def enrich_candidates(
    candidates: list[CandidateSource],
    travel_date: date | None,
    purpose_tag_codes: list[str],
    analysis_repo: AnalysisRepository,
    place_repo: PlaceRepository,
    recommendation_repo: "RecommendationRepository",
    tag_code_by_id: dict[int, str],
) -> list[EnrichedCandidate]:
    """집중률 매핑/판정을 후보에도 재사용해서 congestion_level을 채운다.

    area_cd/signgu_cd는 TourAPI 응답(lDongRegnCd/lDongSignguCd)에서 이미 채워져 있으므로
    STEP4처럼 trip.region_id -> region 매핑을 다시 거치지 않는다. DB 후보 풀 항목은
    지역 코드가 없어(place에 region_id가 비어 있을 수 있음) congestion_level="unknown"으로 둔다.

    후보가 이미 DB에 있는 place(수동 검수를 거쳤을 수 있음)와 연결되면 STEP4와 동일한
    규칙(resolve_reviewed_mapping)으로 승인/거절 판정을 우선 반영한다 — 판정 기준은
    "place가 이미 있는지"가 아니라 "그 place에 approved/rejected 매핑이 있는지"다. place가
    있어도 매핑이 없으면(한 번도 분석된 적 없음) 자동매칭한다. 다만 검수대기(review_required)
    상태는 STEP4와 달리 여기서는 재평가하지 않고 unknown으로 유지한다 — 자동 재매칭이
    우연히 "exact"로 나오면 사람이 검토하기도 전에 확정 등급처럼 보일 수 있기 때문이다.
    STEP4는 기존 동작을 그대로 두므로(범위 밖) 둘 사이에 일시적 비대칭이 생기는데,
    review_required를 진짜로 어떻게 해소할지는 검수 경로 자체를 만드는 후속 이슈에서
    STEP4까지 포함해 같이 정한다 — 과소 확신이 과대 확신보다 안전하다고 판단해 여기서는
    보수적인 쪽을 택한다.
    """
    # 기존 place 일괄 조회 — TourAPI 후보는 (source_type, tour_content_id)로, DB 후보 풀
    # 항목은 candidate.id 자체가 이미 place_id라 별도 조회가 필요 없다. 후보마다
    # get_by_source()를 부르면 후보 수만큼 쿼리가 나가므로 일괄 조회로 묶는다.
    existing_by_source = place_repo.get_by_sources(
        [("tour_api", c.id) for c in candidates if c.from_tour_api]
    )
    # 후보별 existing place를 먼저 전부 확정해야 place_experience_tag도 한 번에 조회할 수
    # 있다 — 아래 본 루프에서 다시 조회하지 않고 이 결과를 그대로 쓴다.
    existing_places: list = [
        existing_by_source.get(("tour_api", c.id))
        if c.from_tour_api
        else place_repo.get_by_id(UUID(c.id))
        for c in candidates
    ]
    tags_by_place = recommendation_repo.list_experience_tags_for_places(
        [p.id for p in existing_places if p is not None]
    )

    enriched: list[EnrichedCandidate] = []
    region_cache: dict[tuple[str, str], tuple] = {}
    for candidate, existing_place in zip(candidates, existing_places):
        mapping = analysis_repo.get_mapping(existing_place.id) if existing_place else None
        if existing_place is None:
            stored_weights: dict[str, float] = {}
            stored_category_weights: dict[str, float] = {}
        else:
            valid_rows = [
                row
                for row in tags_by_place.get(existing_place.id, [])
                if row.experience_tag_id in tag_code_by_id
                and _is_valid_stored_weight(float(row.weight))
            ]
            # source="tour_category"(자동 저장)는 덮어쓰기 우선순위가 아니라 카테고리 근거로만
            # 쓴다 — 그래야 매번 같은 규칙으로 키워드 보완을 다시 얹을 수 있다(resolve_experience_score
            # 문서 참고). 그 외 source는 "사람이 직접 확정했다"고 검증하는 건 아니고, "자동
            # 카테고리 출처가 아니면 보수적으로 우선한다"는 정책으로 덮어쓰기 우선순위로 쓴다.
            stored_category_weights = {
                tag_code_by_id[row.experience_tag_id]: float(row.weight)
                for row in valid_rows
                if row.source == AUTO_CATEGORY_SOURCE
            }
            stored_weights = {
                tag_code_by_id[row.experience_tag_id]: float(row.weight)
                for row in valid_rows
                if row.source != AUTO_CATEGORY_SOURCE
            }

        area_cd, signgu_cd, district_conflict = _resolve_effective_district(
            candidate.area_cd,
            candidate.signgu_cd,
            existing_place.area_cd if existing_place else None,
            existing_place.signgu_cd if existing_place else None,
        )

        if district_conflict:
            spots, items_by_name, api_failed = [], {}, False
        elif area_cd and signgu_cd:
            cache_key = (area_cd, signgu_cd)
            if cache_key not in region_cache:
                region_cache[cache_key] = get_spots_and_items_for_codes(
                    analysis_repo, area_cd, signgu_cd, travel_date
                )
            spots, items_by_name, api_failed = region_cache[cache_key]
        else:
            spots, items_by_name, api_failed = [], {}, False

        if district_conflict or api_failed:
            level = "unknown"
        elif mapping is not None and mapping.status == MappingStatus.REVIEW_REQUIRED:
            # 검수대기는 재평가하지 않는다 — 위 함수 docstring 참고.
            level = "unknown"
        elif mapping is not None and mapping.status in (MappingStatus.APPROVED, MappingStatus.REJECTED):
            # 사람이 이미 확정한 매핑이 있으면 자동 재매칭하지 않고 그 결과를 그대로 쓴다
            # (STEP4의 _apply_reviewed_mapping과 같은 규칙을 resolve_reviewed_mapping으로 공유).
            spot = (
                analysis_repo.get_spot(mapping.concentration_spot_id)
                if mapping.concentration_spot_id is not None
                else None
            )
            resolved_level, _ = resolve_reviewed_mapping(
                mapping, spot, items_by_name, area_cd, signgu_cd
            )
            level = resolved_level or "unknown"
        elif not spots:
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
                experience_score=resolve_experience_score(
                    candidate.name,
                    candidate.category_code,
                    purpose_tag_codes,
                    stored_weights,
                    stored_category_weights,
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
