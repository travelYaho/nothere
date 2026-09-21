"""STEP6 후보 파이프라인(candidates.py) 순수 함수 단위 테스트."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.domains.analysis.service import MappingStatus
from app.domains.recommendation import candidates as candidate_pipeline

# congestion_level 판정만 검증하는 기존 enrich_candidates 테스트들이 쓰는 "태그 없음" 기본값 —
# place_experience_tag 반영 자체를 검증하는 테스트는 별도로 진짜 값을 준비해서 쓴다.
_EMPTY_TAG_CODE_BY_ID: dict[int, str] = {}


def _no_tags_repo():
    repo = MagicMock()
    repo.list_experience_tags_for_places.return_value = {}
    return repo


def test_derive_tag_code_weights_uses_category_and_keywords():
    weights = candidate_pipeline.derive_tag_code_weights("경복궁", "A0201")
    assert weights["history_culture"] >= 0.7


def test_derive_tag_code_weights_keyword_does_not_false_positive_on_hibiscus():
    weights = candidate_pipeline.derive_tag_code_weights("무궁화동산", None)
    assert "history_culture" not in weights


def test_resolve_experience_score_neutral_when_no_purpose_tags():
    score = candidate_pipeline.resolve_experience_score("아무 장소", None, [])
    assert score == candidate_pipeline.SCORE_NO_PURPOSE_SELECTED


def test_resolve_experience_score_rewards_matching_purpose():
    matched = candidate_pipeline.resolve_experience_score("경복궁", "A0201", ["history_culture"])
    mismatched = candidate_pipeline.resolve_experience_score("경복궁", "A0201", ["cafe_rest"])
    assert matched > mismatched


def test_resolve_experience_score_distinguishes_no_evidence_from_mismatch():
    """정보 부족(근거 없음)과 명확한 불일치(근거는 있으나 목적과 안 겹침)는 다른 점수를 받아야
    hard filter(threshold=0.3)와 relaxed_experience(threshold=0.15)가 실제로 다르게 동작한다."""
    no_evidence = candidate_pipeline.resolve_experience_score("이름모를곳", None, ["history_culture"])
    mismatch = candidate_pipeline.resolve_experience_score("경복궁", "A0201", ["cafe_rest"])

    assert no_evidence == candidate_pipeline.SCORE_NO_EVIDENCE
    assert mismatch == candidate_pipeline.SCORE_NO_OVERLAP
    assert mismatch < no_evidence

    # 기본 threshold(0.3)에서는 둘 다 걸러지지만, relaxed(0.15)에서는 "정보 부족"만 살아남는다.
    assert no_evidence < candidate_pipeline.DEFAULT_EXPERIENCE_THRESHOLD
    assert mismatch < candidate_pipeline.DEFAULT_EXPERIENCE_THRESHOLD
    assert no_evidence >= candidate_pipeline.RELAXED_EXPERIENCE_THRESHOLD
    assert mismatch < candidate_pipeline.RELAXED_EXPERIENCE_THRESHOLD


def test_select_top_candidates_sorts_by_experience_score_before_truncating():
    survivors = [
        candidate_pipeline.EnrichedCandidate(
            source=candidate_pipeline.CandidateSource(id=str(i), name=f"장소{i}", latitude=0, longitude=0),
            congestion_level="low",
            experience_score=score,
        )
        for i, score in enumerate([0.4, 0.9, 0.5, 0.6, 0.3, 0.8])
    ]
    top = candidate_pipeline.select_top_candidates(survivors, limit=3)
    assert [c.experience_score for c in top] == [0.9, 0.8, 0.6]


def test_filter_candidates_excludes_duplicate_high_and_low_score():
    survivors_input = [
        candidate_pipeline.EnrichedCandidate(
            source=candidate_pipeline.CandidateSource(id="1", name="중복장소", latitude=0, longitude=0),
            congestion_level="low",
            experience_score=0.9,
        ),
        candidate_pipeline.EnrichedCandidate(
            source=candidate_pipeline.CandidateSource(id="2", name="혼잡장소", latitude=0, longitude=0),
            congestion_level="high",
            experience_score=0.9,
        ),
        candidate_pipeline.EnrichedCandidate(
            source=candidate_pipeline.CandidateSource(id="3", name="저경험", latitude=0, longitude=0),
            congestion_level="low",
            experience_score=0.1,
        ),
        candidate_pipeline.EnrichedCandidate(
            source=candidate_pipeline.CandidateSource(id="4", name="생존장소", latitude=0, longitude=0),
            congestion_level="mid",
            experience_score=0.5,
        ),
    ]
    survivors, excluded = candidate_pipeline.filter_candidates(
        survivors_input, duplicate_names={"중복장소"}, experience_threshold=0.3
    )
    assert excluded == 3
    assert [c.source.name for c in survivors] == ["생존장소"]


def test_generate_candidates_falls_back_to_db_pool_when_tour_api_empty(monkeypatch):
    monkeypatch.setattr(candidate_pipeline, "fetch_nearby_places", lambda lat, lng, radius_m: [])

    def fake_pool(radius_m):
        return [{"id": "abc", "name": "DB후보", "lat": 37.5, "lng": 127.0}]

    result = candidate_pipeline.generate_candidates(37.5, 127.0, 3.0, db_pool_fetcher=fake_pool)
    assert len(result) == 1
    assert result[0].id == "abc"
    assert result[0].from_tour_api is False


# --- _resolve_effective_district (순수 함수) ---

def test_resolve_effective_district_no_existing_place_uses_candidate_codes():
    assert candidate_pipeline._resolve_effective_district("11", "11110", None, None) == ("11", "11110", False)


def test_resolve_effective_district_candidate_missing_falls_back_to_stored():
    assert candidate_pipeline._resolve_effective_district(None, None, "11", "11110") == ("11", "11110", False)


def test_resolve_effective_district_matching_codes_no_conflict():
    assert candidate_pipeline._resolve_effective_district("11", "11110", "11", "11110") == ("11", "11110", False)


def test_resolve_effective_district_mismatch_is_conflict():
    assert candidate_pipeline._resolve_effective_district("11", "11110", "26", "26290") == (None, None, True)


def test_resolve_effective_district_partial_stored_area_conflicts_with_new_area():
    """저장된 place가 area_cd만 있고(signgu_cd는 아직 없음) 그 area_cd가 새 응답과 다르면,
    signgu_cd가 없다는 이유로 무시하지 않고 area_cd 단독으로도 충돌을 잡아야 한다 —
    저장소 백필(_classify_district_code_backfill)과 같은 필드 단위 규칙(2라운드 리뷰로 발견)."""
    assert candidate_pipeline._resolve_effective_district("26", "26110", "11", None) == (None, None, True)


def test_resolve_effective_district_partial_stored_area_matches_new_area():
    """저장된 area_cd가 새 응답과 같고 signgu_cd만 이번에 채워지는 경우는 충돌이 아니라
    정상적으로 백필 가능한 상태다."""
    assert candidate_pipeline._resolve_effective_district("11", "11290", "11", None) == ("11", "11290", False)


# --- enrich_candidates: 수동 검수 매핑 반영 (2026-09-15) ---

def _spot(area_cd="11", signgu_cd="11110", name="경국사"):
    return SimpleNamespace(id=1, tourist_name=name, area_cd=area_cd, signgu_cd=signgu_cd)


def _place(place_id=None, area_cd="11", signgu_cd="11110"):
    return SimpleNamespace(id=place_id or uuid4(), area_cd=area_cd, signgu_cd=signgu_cd)


def test_enrich_candidates_respects_approved_mapping_over_automatic_match(monkeypatch):
    """place가 이미 있고 approved 매핑이 있으면, 자동매칭이 다른 결과를 내더라도 승인된
    판정을 그대로 쓴다."""
    place_id = uuid4()
    existing_place = _place(place_id)
    approved_spot = _spot(name="승인된진짜장소")
    mapping = SimpleNamespace(status=MappingStatus.APPROVED, concentration_spot_id=1)

    # 자동매칭을 돌리면 완전히 다른(틀린) spot이 걸릴 상황을 흉내낸다.
    decoy_spot = _spot(name="자동매칭이_고를_엉뚱한장소")
    monkeypatch.setattr(
        candidate_pipeline,
        "get_spots_and_items_for_codes",
        lambda repo, area_cd, signgu_cd, travel_date: (
            [decoy_spot],
            {"승인된진짜장소": SimpleNamespace(raw_value=10.0, base_ymd="20260910")},
            False,
        ),
    )

    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = mapping
    analysis_repo.get_spot.return_value = approved_spot

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="아무이름", latitude=37.5, longitude=127.0,
        area_cd="11", signgu_cd="11110", from_tour_api=True,
    )

    result = candidate_pipeline.enrich_candidates(
        [candidate], None, [], analysis_repo, place_repo, _no_tags_repo(), _EMPTY_TAG_CODE_BY_ID
    )

    assert result[0].congestion_level == candidate_pipeline.ConcentrationLevel.LOW
    analysis_repo.get_mapping.assert_called_once_with(place_id)


def test_enrich_candidates_rejected_mapping_is_unknown_without_automatic_rematch(monkeypatch):
    place_id = uuid4()
    existing_place = _place(place_id)
    mapping = SimpleNamespace(status=MappingStatus.REJECTED, concentration_spot_id=None)

    called = {"match": False}

    def fake_match(*args, **kwargs):
        called["match"] = True
        return SimpleNamespace(spot=None, status="no_mapping")

    monkeypatch.setattr(
        candidate_pipeline,
        "get_spots_and_items_for_codes",
        lambda repo, area_cd, signgu_cd, travel_date: ([_spot()], {}, False),
    )
    monkeypatch.setattr(candidate_pipeline, "match_concentration_spot", fake_match)

    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = mapping

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="아무이름", latitude=37.5, longitude=127.0,
        area_cd="11", signgu_cd="11110", from_tour_api=True,
    )

    result = candidate_pipeline.enrich_candidates(
        [candidate], None, [], analysis_repo, place_repo, _no_tags_repo(), _EMPTY_TAG_CODE_BY_ID
    )

    assert result[0].congestion_level == "unknown"
    assert called["match"] is False  # 거절된 매핑이 있으면 자동 재매칭 자체를 안 함


def test_enrich_candidates_auto_matches_when_place_exists_without_mapping(monkeypatch):
    """place가 이미 있어도 검수 매핑(approved/rejected)이 없으면(한 번도 분석 안 됨)
    자동매칭을 한다 — 판정 기준은 place 존재 여부가 아니라 매핑 유무여야 한다."""
    place_id = uuid4()
    existing_place = _place(place_id)
    spot = _spot(name="자동매칭대상")

    monkeypatch.setattr(
        candidate_pipeline,
        "get_spots_and_items_for_codes",
        lambda repo, area_cd, signgu_cd, travel_date: (
            [spot],
            {"자동매칭대상": SimpleNamespace(raw_value=90.0, base_ymd="20260910")},
            False,
        ),
    )

    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None  # 매핑 자체가 없음

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="자동매칭대상", latitude=37.5, longitude=127.0,
        area_cd="11", signgu_cd="11110", from_tour_api=True,
    )

    result = candidate_pipeline.enrich_candidates(
        [candidate], None, [], analysis_repo, place_repo, _no_tags_repo(), _EMPTY_TAG_CODE_BY_ID
    )

    assert result[0].congestion_level == candidate_pipeline.ConcentrationLevel.HIGH
    analysis_repo.get_spot.assert_not_called()  # 검수 판정 경로를 안 탔는지 확인


def test_enrich_candidates_db_pool_candidate_respects_own_mapping(monkeypatch):
    """DB 후보 풀 항목(from_tour_api=False)은 candidate.id 자체가 place_id다 —
    get_by_sources()가 아니라 get_by_ids()로 조회되고, 그 place의 검수 결과를 따라야 한다."""
    place_id = uuid4()
    existing_place = _place(place_id)
    approved_spot = _spot(name="DB후보장소")
    mapping = SimpleNamespace(status=MappingStatus.APPROVED, concentration_spot_id=1)

    monkeypatch.setattr(
        candidate_pipeline,
        "get_spots_and_items_for_codes",
        lambda repo, area_cd, signgu_cd, travel_date: (
            [],
            {"DB후보장소": SimpleNamespace(raw_value=10.0, base_ymd="20260910")},
            False,
        ),
    )

    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {}
    place_repo.get_by_ids.return_value = {place_id: existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = mapping
    analysis_repo.get_spot.return_value = approved_spot

    candidate = candidate_pipeline.CandidateSource(
        id=str(place_id), name="DB후보장소", latitude=37.5, longitude=127.0,
        area_cd="11", signgu_cd="11110", from_tour_api=False,
    )

    result = candidate_pipeline.enrich_candidates(
        [candidate], None, [], analysis_repo, place_repo, _no_tags_repo(), _EMPTY_TAG_CODE_BY_ID
    )

    assert result[0].congestion_level == candidate_pipeline.ConcentrationLevel.LOW
    place_repo.get_by_ids.assert_called_once_with([place_id])
    place_repo.get_by_id.assert_not_called()
    place_repo.get_by_sources.assert_called_once_with([])


def test_enrich_candidates_db_pool_candidates_batch_get_by_ids(monkeypatch):
    """DB fallback 후보 10개는 get_by_id() 10회가 아니라 get_by_ids() 1회로 묶인다."""
    monkeypatch.setattr(
        candidate_pipeline,
        "get_spots_and_items_for_codes",
        lambda repo, area_cd, signgu_cd, travel_date: ([], {}, False),
    )

    place_ids = [uuid4() for _ in range(10)]
    places_by_id = {place_id: _place(place_id) for place_id in place_ids}
    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {}
    place_repo.get_by_ids.return_value = places_by_id
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None

    candidates = [
        candidate_pipeline.CandidateSource(
            id=str(place_id), name=f"DB후보{i}", latitude=37.5, longitude=127.0,
            area_cd="11", signgu_cd="11110", from_tour_api=False,
        )
        for i, place_id in enumerate(place_ids)
    ]

    result = candidate_pipeline.enrich_candidates(
        candidates, None, [], analysis_repo, place_repo, _no_tags_repo(), _EMPTY_TAG_CODE_BY_ID
    )

    assert len(result) == 10
    place_repo.get_by_ids.assert_called_once_with(place_ids)
    place_repo.get_by_id.assert_not_called()
    place_repo.get_by_sources.assert_called_once_with([])


def test_enrich_candidates_existing_review_required_stays_unknown_even_if_rematch_would_be_exact(monkeypatch):
    """기존 매핑이 review_required면 STEP4와 달리 재평가하지 않는다 — 자동 재매칭이 우연히
    exact로 나와도 사람이 검토하기 전엔 확정 등급으로 보여주지 않는다(코드 리뷰로 발견,
    2026-09-15)."""
    existing_place = _place()
    mapping = SimpleNamespace(status=MappingStatus.REVIEW_REQUIRED, concentration_spot_id=None)

    called = {"match": False}

    def fake_match(*args, **kwargs):
        called["match"] = True
        return SimpleNamespace(spot=_spot(), match_method="exact", confidence=1.0, status=MappingStatus.AUTO_APPROVED)

    monkeypatch.setattr(
        candidate_pipeline,
        "get_spots_and_items_for_codes",
        lambda repo, area_cd, signgu_cd, travel_date: (
            [_spot()], {"경국사": SimpleNamespace(raw_value=10.0, base_ymd="20260910")}, False,
        ),
    )
    monkeypatch.setattr(candidate_pipeline, "match_concentration_spot", fake_match)

    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = mapping

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="경국사", latitude=37.5, longitude=127.0,
        area_cd="11", signgu_cd="11110", from_tour_api=True,
    )

    result = candidate_pipeline.enrich_candidates(
        [candidate], None, [], analysis_repo, place_repo, _no_tags_repo(), _EMPTY_TAG_CODE_BY_ID
    )

    assert result[0].congestion_level == "unknown"
    assert called["match"] is False  # review_required도 재매칭 자체를 안 함


def test_enrich_candidates_district_conflict_with_stored_place_yields_unknown(monkeypatch):
    """이번 TourAPI 응답의 지역코드가 기존 place에 저장된 지역코드와 다르면, 실제 적용 시
    backfill 충돌 감지로 기존 값이 유지될 것이므로 확정 등급을 내지 않는다 — 지금 보여준
    값과 나중에 STEP4가 보여줄 값이 서로 다른 지역 기준이 되는 걸 막는다."""
    existing_place = _place(area_cd="26", signgu_cd="26290")  # 저장된 place는 부산(26)
    called = {"api": False}

    def fake_get_spots(*args, **kwargs):
        called["api"] = True
        return [_spot()], {}, False

    monkeypatch.setattr(candidate_pipeline, "get_spots_and_items_for_codes", fake_get_spots)

    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="아무이름", latitude=37.5, longitude=127.0,
        area_cd="11", signgu_cd="11110", from_tour_api=True,  # 이번 응답은 서울(11) — 충돌
    )

    result = candidate_pipeline.enrich_candidates(
        [candidate], None, [], analysis_repo, place_repo, _no_tags_repo(), _EMPTY_TAG_CODE_BY_ID
    )

    assert result[0].congestion_level == "unknown"
    assert called["api"] is False  # 충돌이면 집중률 API 조회 자체를 안 함(불필요한 호출 방지)


def test_enrich_candidates_uses_stored_district_when_response_omits_it(monkeypatch):
    """이번 응답에 지역코드가 없어도 기존 place에 유효한 코드가 있으면 그걸로 조회한다 —
    "지역코드 없음"으로 단정해 무조건 unknown 처리하지 않는다."""
    existing_place = _place(area_cd="11", signgu_cd="11110")
    spot = _spot(area_cd="11", signgu_cd="11110", name="저장된장소")

    monkeypatch.setattr(
        candidate_pipeline,
        "get_spots_and_items_for_codes",
        lambda repo, area_cd, signgu_cd, travel_date: (
            [spot],
            {"저장된장소": SimpleNamespace(raw_value=10.0, base_ymd="20260910")},
            False,
        ) if (area_cd, signgu_cd) == ("11", "11110") else (_ for _ in ()).throw(
            AssertionError(f"저장된 지역코드를 안 썼음: {area_cd}, {signgu_cd}")
        ),
    )

    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="저장된장소", latitude=37.5, longitude=127.0,
        area_cd=None, signgu_cd=None, from_tour_api=True,  # 이번 응답엔 지역코드 없음
    )

    result = candidate_pipeline.enrich_candidates(
        [candidate], None, [], analysis_repo, place_repo, _no_tags_repo(), _EMPTY_TAG_CODE_BY_ID
    )

    assert result[0].congestion_level == candidate_pipeline.ConcentrationLevel.LOW


# --- _combine_tag_weights (순수 함수) ---

def test_combine_tag_weights_stored_value_wins_over_estimate():
    combined = candidate_pipeline._combine_tag_weights(
        stored_weights={"history_culture": 0.2}, estimated_weights={"history_culture": 1.0}
    )
    assert combined["history_culture"] == 0.2  # 저장값이 이겨야 한다(추정값으로 안 덮임)


def test_combine_tag_weights_fills_gaps_with_estimate():
    combined = candidate_pipeline._combine_tag_weights(
        stored_weights={"history_culture": 0.2},
        estimated_weights={"history_culture": 1.0, "cafe_rest": 0.4},
    )
    assert combined == {"history_culture": 0.2, "cafe_rest": 0.4}  # 없는 태그만 추정으로 보완


def test_combine_tag_weights_no_stored_uses_pure_estimate():
    combined = candidate_pipeline._combine_tag_weights(
        stored_weights={}, estimated_weights={"nature_walk": 0.6}
    )
    assert combined == {"nature_walk": 0.6}


# --- resolve_experience_score: 저장된 place_experience_tag 우선 반영 ---

def test_resolve_experience_score_uses_stored_weight_over_estimate():
    """저장된 가중치가 카테고리 추정치와 다르면(예: 사람이 나중에 수정한 값) 저장값을 써야
    한다 — mock_experience_score였을 때는 place_experience_tag를 아예 안 읽었다."""
    # A0201(역사관광지) 카테고리 추정은 history_culture=1.0이지만, 저장된 값은 0.1로 낮다.
    score_with_low_stored = candidate_pipeline.resolve_experience_score(
        "아무이름", "A0201", ["history_culture"], stored_weights={"history_culture": 0.1}
    )
    score_pure_estimate = candidate_pipeline.resolve_experience_score(
        "아무이름", "A0201", ["history_culture"], stored_weights=None
    )
    assert score_with_low_stored < score_pure_estimate


def test_resolve_experience_score_no_stored_weights_falls_back_to_estimate():
    """place_experience_tag가 없는(신규) 후보는 기존 추정 규칙만 쓴다 — 동작 변화 없음."""
    assert candidate_pipeline.resolve_experience_score(
        "경복궁", "A0201", ["history_culture"], stored_weights={}
    ) == candidate_pipeline.resolve_experience_score(
        "경복궁", "A0201", ["history_culture"], stored_weights=None
    )


# --- enrich_candidates: 저장된 경험 태그가 실제로 점수에 반영됨(이슈3, 2026-09-16) ---

def test_enrich_candidates_uses_stored_experience_tags_in_score():
    existing_place = _place()
    recommendation_repo = MagicMock()
    # experience_tag_id=2 -> "history_culture", 저장된 weight=0.1(낮음, 카테고리 추정 1.0보다 훨씬 낮음)
    # source="manual" -> 사람이 확정한 값이라 덮어쓰기 우선순위(하드 override)로 들어간다.
    recommendation_repo.list_experience_tags_for_places.return_value = {
        existing_place.id: [SimpleNamespace(experience_tag_id=2, weight=0.1, source="manual")]
    }
    tag_code_by_id = {2: "history_culture"}

    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="아무이름", latitude=37.5, longitude=127.0,
        category_code="A0201", from_tour_api=True,  # area_cd/signgu_cd 없음 -> congestion은 무관
    )

    result = candidate_pipeline.enrich_candidates(
        [candidate], None, ["history_culture"], analysis_repo, place_repo,
        recommendation_repo, tag_code_by_id,
    )

    recommendation_repo.list_experience_tags_for_places.assert_called_once_with([existing_place.id])
    expected = candidate_pipeline.resolve_experience_score(
        "아무이름", "A0201", ["history_culture"], stored_weights={"history_culture": 0.1}
    )
    assert result[0].experience_score == expected
    # 저장값(0.1)이 카테고리 추정치(1.0)보다 훨씬 낮으므로 점수도 순수 추정보다 낮아야 한다.
    pure_estimate_score = candidate_pipeline.resolve_experience_score(
        "아무이름", "A0201", ["history_culture"], stored_weights=None
    )
    assert result[0].experience_score < pure_estimate_score


def test_enrich_candidates_new_candidate_without_place_uses_pure_estimate():
    """place_experience_tag가 없는(한 번도 저장된 적 없는) 신규 후보는 추정 규칙만 쓴다."""
    recommendation_repo = MagicMock()
    recommendation_repo.list_experience_tags_for_places.return_value = {}

    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {}  # 기존 place 없음
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None

    candidate = candidate_pipeline.CandidateSource(
        id="new-content", name="경복궁", latitude=37.5, longitude=127.0,
        category_code="A0201", from_tour_api=True,
    )

    result = candidate_pipeline.enrich_candidates(
        [candidate], None, ["history_culture"], analysis_repo, place_repo,
        recommendation_repo, {2: "history_culture"},
    )

    # 기존 place가 없으므로 list_experience_tags_for_places는 빈 place_id 목록으로 불린다.
    recommendation_repo.list_experience_tags_for_places.assert_called_once_with([])
    expected = candidate_pipeline.resolve_experience_score(
        "경복궁", "A0201", ["history_culture"], stored_weights=None
    )
    assert result[0].experience_score == expected


def test_enrich_candidates_manual_zero_weight_is_not_overwritten_by_estimate():
    """저장된 수동 가중치 0.0은 '그 경험과 무관함'이라는 유효한 값이라, 카테고리 추정치로
    되돌아가면 안 된다(setdefault가 0.0을 '없음'으로 착각하지 않는지 확인)."""
    recommendation_repo = MagicMock()
    existing_place = _place()
    recommendation_repo.list_experience_tags_for_places.return_value = {
        existing_place.id: [SimpleNamespace(experience_tag_id=2, weight=0.0, source="manual")]
    }
    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="아무이름", latitude=37.5, longitude=127.0,
        category_code="A0201", from_tour_api=True,
    )
    result = candidate_pipeline.enrich_candidates(
        [candidate], None, ["history_culture"], analysis_repo, place_repo,
        recommendation_repo, {2: "history_culture"},
    )

    expected = candidate_pipeline.resolve_experience_score(
        "아무이름", "A0201", ["history_culture"], stored_weights={"history_culture": 0.0}
    )
    assert result[0].experience_score == expected
    # 카테고리 추정치(1.0)로 되돌아갔다면 이보다 높은 점수가 나왔을 것 — 0.0이 진짜로 쓰였는지 확인.
    pure_estimate_score = candidate_pipeline.resolve_experience_score(
        "아무이름", "A0201", ["history_culture"], stored_weights=None
    )
    assert result[0].experience_score < pure_estimate_score


def test_enrich_candidates_out_of_range_stored_weight_falls_back_to_estimate():
    """weight가 [0,1] 범위를 벗어나거나 NaN이면 데이터 오류로 보고 버리고, 해당 태그는
    카테고리·키워드 추정값으로 대체돼야 한다."""
    existing_place = _place()
    recommendation_repo = MagicMock()
    recommendation_repo.list_experience_tags_for_places.return_value = {
        existing_place.id: [SimpleNamespace(experience_tag_id=2, weight=1.5, source="manual")]
    }
    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="아무이름", latitude=37.5, longitude=127.0,
        category_code="A0201", from_tour_api=True,
    )
    result = candidate_pipeline.enrich_candidates(
        [candidate], None, ["history_culture"], analysis_repo, place_repo,
        recommendation_repo, {2: "history_culture"},
    )

    # 잘못된 저장값(1.5)은 버려져서 순수 추정("A0201" 카테고리 추정)과 같은 점수가 나와야 한다.
    pure_estimate_score = candidate_pipeline.resolve_experience_score(
        "아무이름", "A0201", ["history_culture"], stored_weights=None
    )
    assert result[0].experience_score == pure_estimate_score


def test_enrich_candidates_stored_weight_change_flips_filter_outcome():
    """저장된 가중치가 낮아지면 hard filter(low_experience_score)에서 실제로 걸러져야
    한다 — 점수 계산만이 아니라 필터링 결과까지 저장값 변경이 반영되는지 확인."""
    existing_place = _place()

    def _run_with_stored_weight(weight):
        recommendation_repo = MagicMock()
        recommendation_repo.list_experience_tags_for_places.return_value = {
            existing_place.id: [SimpleNamespace(experience_tag_id=2, weight=weight, source="manual")]
        }
        place_repo = MagicMock()
        place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
        analysis_repo = MagicMock()
        analysis_repo.get_mapping.return_value = None

        candidate = candidate_pipeline.CandidateSource(
            id="content-1", name="아무이름", latitude=37.5, longitude=127.0,
            category_code="A0201", from_tour_api=True,
        )
        enriched = candidate_pipeline.enrich_candidates(
            [candidate], None, ["history_culture"], analysis_repo, place_repo,
            recommendation_repo, {2: "history_culture"},
        )
        survivors, _ = candidate_pipeline.filter_candidates(
            enriched, set(), candidate_pipeline.DEFAULT_EXPERIENCE_THRESHOLD
        )
        return survivors

    assert _run_with_stored_weight(1.0)  # 높은 저장값 -> threshold 통과, 살아남음
    assert not _run_with_stored_weight(0.0)  # 낮은 저장값 -> threshold 미달, 걸러짐


def test_enrich_candidates_score_stable_across_first_save_and_requery(monkeypatch):
    """카테고리 근거만 저장하고(키워드는 저장 안 함) 재요청해도, 같은 입력이면 첫 요청과
    같은 점수가 나와야 한다 — 카테고리 저장값을 덮어쓰기 우선순위로 쓰면 재요청부터
    키워드 보완이 사라져 점수가 달라졌던 회귀(2026-09-16, 2라운드 코드 리뷰로 발견)를 막는다.

    시나리오(리뷰에서 제시한 예시 그대로): "전망타워"(A0205=architecture_space:1.0,
    photo_view:0.5), 목적 photo_view. 이름 키워드 "전망"이 photo_view를 0.7로 끌어올린다.
    - 1차 요청(태그 미저장): category_only_tag_weights(A0205)+키워드 보완 = photo_view 0.7.
    - 저장: category_only_tag_weights(A0205)만 DB에 들어감(photo_view=0.5, 키워드 없음).
    - 2차 요청(태그 저장됨, source="tour_category"): 저장된 카테고리값(0.5) 위에 키워드
      보완(0.7)을 다시 얹어야 하므로 photo_view는 여전히 0.7 — 1차와 같은 점수여야 한다.
    """
    existing_place = _place()
    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None
    tag_code_by_id = {1: "architecture_space", 2: "photo_view"}

    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="전망타워", latitude=37.5, longitude=127.0,
        category_code="A0205", from_tour_api=True,
    )

    # 1차 요청: 저장된 태그 없음.
    first_repo = MagicMock()
    first_repo.list_experience_tags_for_places.return_value = {}
    first_result = candidate_pipeline.enrich_candidates(
        [candidate], None, ["photo_view"], analysis_repo, place_repo, first_repo, tag_code_by_id,
    )

    # 저장: 실제 _materialize_candidate가 하는 것과 똑같이 category_only_tag_weights만 저장.
    stored_category_weights = candidate_pipeline.category_only_tag_weights("A0205")
    assert stored_category_weights == {"architecture_space": 1.0, "photo_view": 0.5}
    assert "photo_view" not in candidate_pipeline._keyword_tag_weights("아무키워드없음")  # 키워드는 저장 대상이 아님을 재확인

    # 2차 요청: 방금 저장된 카테고리 태그만(source="tour_category") 반영.
    second_repo = MagicMock()
    second_repo.list_experience_tags_for_places.return_value = {
        existing_place.id: [
            SimpleNamespace(experience_tag_id=1, weight=1.0, source="tour_category"),
            SimpleNamespace(experience_tag_id=2, weight=0.5, source="tour_category"),
        ]
    }
    second_result = candidate_pipeline.enrich_candidates(
        [candidate], None, ["photo_view"], analysis_repo, place_repo, second_repo, tag_code_by_id,
    )

    assert first_result[0].experience_score == second_result[0].experience_score
    expected = candidate_pipeline.resolve_experience_score("전망타워", "A0205", ["photo_view"])
    assert first_result[0].experience_score == expected == 0.805


def test_enrich_candidates_score_stable_when_auto_tags_partially_stored():
    """자동 카테고리 태그가 일부만 저장된 상태에서도, 저장 안 된 나머지 태그는 라이브
    카테고리 계산으로 채워져야 한다 — "저장값이 하나라도 있으면 라이브 계산 전체를 버리는"
    방식이면, DO NOTHING으로 나머지 태그가 나중에 채워지는 순간부터 그 태그가 갑자기
    점수에 반영되어 같은 입력인데도 저장 시점에 따라 결과가 달라진다(2026-09-17, 3라운드
    코드 리뷰로 발견·수정).

    시나리오: A0205 카테고리 근거는 architecture_space=1.0, photo_view=0.5인데, DB엔
    photo_view=0.5만 저장돼 있고(부분 저장) architecture_space는 아직 없다. 목적은
    architecture_space — 부분 저장 상태에서도 라이브 카테고리 계산으로 architecture_space가
    채워져야 하고, architecture_space까지 마저 저장된 뒤에도 점수가 똑같아야 한다.
    """
    existing_place = _place()
    place_repo = MagicMock()
    place_repo.get_by_sources.return_value = {("tour_api", "content-1"): existing_place}
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = None
    tag_code_by_id = {1: "architecture_space", 2: "photo_view"}

    # 이름 키워드가 개입하지 않도록 어느 EXPERIENCE_TAG_KEYWORDS에도 안 걸리는 이름을 쓴다.
    candidate = candidate_pipeline.CandidateSource(
        id="content-1", name="아무이름", latitude=37.5, longitude=127.0,
        category_code="A0205", from_tour_api=True,
    )

    # 부분 저장: photo_view만 DB에 있고 architecture_space는 없음.
    partial_repo = MagicMock()
    partial_repo.list_experience_tags_for_places.return_value = {
        existing_place.id: [SimpleNamespace(experience_tag_id=2, weight=0.5, source="tour_category")]
    }
    partial_result = candidate_pipeline.enrich_candidates(
        [candidate], None, ["architecture_space"], analysis_repo, place_repo, partial_repo,
        tag_code_by_id,
    )

    # 라이브 카테고리 계산으로 architecture_space=1.0이 채워져야 한다 — SCORE_NO_OVERLAP(0.05)로
    # 떨어지면 부분 저장 때문에 architecture_space 근거 자체가 통째로 사라졌다는 뜻(버그 재현).
    assert partial_result[0].experience_score != candidate_pipeline.SCORE_NO_OVERLAP
    full_estimate = candidate_pipeline.resolve_experience_score(
        "아무이름", "A0205", ["architecture_space"]
    )
    assert partial_result[0].experience_score == full_estimate == 1.0

    # 완전 저장(architecture_space까지 채워짐) 이후 재요청해도 점수는 그대로여야 한다.
    full_repo = MagicMock()
    full_repo.list_experience_tags_for_places.return_value = {
        existing_place.id: [
            SimpleNamespace(experience_tag_id=1, weight=1.0, source="tour_category"),
            SimpleNamespace(experience_tag_id=2, weight=0.5, source="tour_category"),
        ]
    }
    full_result = candidate_pipeline.enrich_candidates(
        [candidate], None, ["architecture_space"], analysis_repo, place_repo, full_repo,
        tag_code_by_id,
    )
    assert full_result[0].experience_score == partial_result[0].experience_score
