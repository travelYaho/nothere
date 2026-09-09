"""STEP6 후보 파이프라인(candidates.py) 순수 함수 단위 테스트."""
from __future__ import annotations

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
