"""AnalysisRepository.upsert_mapping 의 수동 검수(approved/rejected) 보존 규칙 테스트."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.repositories.analysis_repository import AnalysisRepository


def _repo_with_existing(existing) -> tuple[AnalysisRepository, MagicMock]:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing
    return AnalysisRepository(db), db


def test_upsert_mapping_preserves_human_approved_even_with_new_match():
    existing = SimpleNamespace(status="approved", concentration_spot_id=1)
    repo, db = _repo_with_existing(existing)

    result = repo.upsert_mapping("place-1", 999, "exact", None, "auto_approved")

    assert result is existing
    assert existing.concentration_spot_id == 1  # 덮어써지지 않음
    db.commit.assert_not_called()
    db.delete.assert_not_called()


def test_upsert_mapping_preserves_human_rejected_when_no_match_found():
    existing = SimpleNamespace(status="rejected", concentration_spot_id=None)
    repo, db = _repo_with_existing(existing)

    result = repo.upsert_mapping("place-1", None, None, None, "no_mapping")

    assert result is existing
    db.delete.assert_not_called()


def test_upsert_mapping_overwrites_when_not_human_reviewed():
    existing = SimpleNamespace(status="auto_approved", concentration_spot_id=1)
    repo, db = _repo_with_existing(existing)

    result = repo.upsert_mapping("place-1", 2, "fuzzy", None, "review_required")

    assert result.concentration_spot_id == 2
    assert result.status == "review_required"
    db.commit.assert_called_once()


def test_upsert_mapping_deletes_when_no_match_and_not_human_reviewed():
    existing = SimpleNamespace(status="auto_approved", concentration_spot_id=1)
    repo, db = _repo_with_existing(existing)

    result = repo.upsert_mapping("place-1", None, None, None, "no_mapping")

    assert result is None
    db.delete.assert_called_once_with(existing)
