"""STEP6 후보 파이프라인(candidates.py) 순수 함수 단위 테스트."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.domains.analysis.service import MappingStatus
from app.domains.recommendation import candidates as candidate_pipeline


def test_derive_tag_code_weights_uses_category_and_keywords():
    weights = candidate_pipeline.derive_tag_code_weights("경복궁", "A0201")
    assert weights["history_culture"] >= 0.7


def test_derive_tag_code_weights_keyword_does_not_false_positive_on_hibiscus():
    weights = candidate_pipeline.derive_tag_code_weights("무궁화동산", None)
    assert "history_culture" not in weights


def test_mock_experience_score_neutral_when_no_purpose_tags():
    score = candidate_pipeline.mock_experience_score("아무 장소", None, [])
    assert score == candidate_pipeline.SCORE_NO_PURPOSE_SELECTED


def test_mock_experience_score_rewards_matching_purpose():
    matched = candidate_pipeline.mock_experience_score("경복궁", "A0201", ["history_culture"])
    mismatched = candidate_pipeline.mock_experience_score("경복궁", "A0201", ["cafe_rest"])
    assert matched > mismatched


def test_mock_experience_score_distinguishes_no_evidence_from_mismatch():
    """정보 부족(근거 없음)과 명확한 불일치(근거는 있으나 목적과 안 겹침)는 다른 점수를 받아야
    hard filter(threshold=0.3)와 relaxed_experience(threshold=0.15)가 실제로 다르게 동작한다."""
    no_evidence = candidate_pipeline.mock_experience_score("이름모를곳", None, ["history_culture"])
    mismatch = candidate_pipeline.mock_experience_score("경복궁", "A0201", ["cafe_rest"])

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

    result = candidate_pipeline.enrich_candidates([candidate], None, [], analysis_repo, place_repo)

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

    result = candidate_pipeline.enrich_candidates([candidate], None, [], analysis_repo, place_repo)

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

    result = candidate_pipeline.enrich_candidates([candidate], None, [], analysis_repo, place_repo)

    assert result[0].congestion_level == candidate_pipeline.ConcentrationLevel.HIGH
    analysis_repo.get_spot.assert_not_called()  # 검수 판정 경로를 안 탔는지 확인


def test_enrich_candidates_db_pool_candidate_respects_own_mapping(monkeypatch):
    """DB 후보 풀 항목(from_tour_api=False)은 candidate.id 자체가 place_id다 —
    get_by_sources()가 아니라 get_by_id()로 조회되고, 그 place의 검수 결과를 따라야 한다."""
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
    place_repo.get_by_id.return_value = existing_place
    analysis_repo = MagicMock()
    analysis_repo.get_mapping.return_value = mapping
    analysis_repo.get_spot.return_value = approved_spot

    candidate = candidate_pipeline.CandidateSource(
        id=str(place_id), name="DB후보장소", latitude=37.5, longitude=127.0,
        area_cd="11", signgu_cd="11110", from_tour_api=False,
    )

    result = candidate_pipeline.enrich_candidates([candidate], None, [], analysis_repo, place_repo)

    assert result[0].congestion_level == candidate_pipeline.ConcentrationLevel.LOW
    place_repo.get_by_id.assert_called_once_with(place_id)
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

    result = candidate_pipeline.enrich_candidates([candidate], None, [], analysis_repo, place_repo)

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

    result = candidate_pipeline.enrich_candidates([candidate], None, [], analysis_repo, place_repo)

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

    result = candidate_pipeline.enrich_candidates([candidate], None, [], analysis_repo, place_repo)

    assert result[0].congestion_level == candidate_pipeline.ConcentrationLevel.LOW
