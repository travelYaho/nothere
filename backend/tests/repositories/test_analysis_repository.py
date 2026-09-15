"""AnalysisRepository.upsert_mapping 의 수동 검수(approved/rejected) 보존 규칙 테스트."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy.dialects import postgresql

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


# --- bulk_upsert_spots ---

def test_bulk_upsert_spots_inserts_once_and_does_not_commit():
    """개수와 무관하게 execute 1번(INSERT)+list_spots_by_region 조회 1번만 하고, commit은
    저장소가 아니라 호출부 책임이므로 여기선 절대 호출하지 않는다."""
    db = MagicMock()
    repo = AnalysisRepository(db)
    expected_spots = [SimpleNamespace(id=1, tourist_name="경국사")]
    repo.list_spots_by_region = MagicMock(return_value=expected_spots)

    result = repo.bulk_upsert_spots(
        "11", "11290", [("경국사", "경국사"), ("길상사", "길상사"), ("길음시장", "길음시장")]
    )

    assert result is expected_spots
    db.execute.assert_called_once()  # INSERT 문 1번만
    db.commit.assert_not_called()
    repo.list_spots_by_region.assert_called_once_with("11", "11290")


def test_bulk_upsert_spots_uses_on_conflict_do_nothing_on_area_signgu_name_columns():
    """이미 있는 관광지는(같은 area_cd/signgu_cd/tourist_name) INSERT가 조용히 무시돼야
    기존 행(id, 참조 중인 PlaceConcentrationMapping 포함)이 그대로 보존된다 — 컴파일된
    SQL에 ON CONFLICT DO NOTHING이 들어갔는지, 대상 컬럼이 정확한지 직접 확인한다.

    이름(constraint=...)이 아니라 컬럼 조합(index_elements=...)으로 지정한다 — 실제 테이블을
    만드는 schema.sql은 이름 없는 인라인 UNIQUE를 쓰므로 ORM 모델의 제약 이름이 실제 DB에는
    없다(Docker 격리 DB로 실제 검증하다가 발견한 불일치, 2026-09-13).
    """
    db = MagicMock()
    repo = AnalysisRepository(db)
    repo.list_spots_by_region = MagicMock(return_value=[])

    repo.bulk_upsert_spots("11", "11290", [("경국사", "경국사")])

    stmt = db.execute.call_args[0][0]
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT" in compiled
    assert "DO NOTHING" in compiled
    assert "(area_cd, signgu_cd, tourist_name)" in compiled


def test_bulk_upsert_spots_skips_insert_when_no_spots():
    db = MagicMock()
    repo = AnalysisRepository(db)
    repo.list_spots_by_region = MagicMock(return_value=[])

    result = repo.bulk_upsert_spots("11", "11290", [])

    assert result == []
    db.execute.assert_not_called()
    db.commit.assert_not_called()
