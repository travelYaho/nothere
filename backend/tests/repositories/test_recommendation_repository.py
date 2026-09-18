"""RecommendationRepository의 배치 조회 메서드를 검증한다."""
from unittest.mock import MagicMock
from uuid import uuid4

from app.repositories.recommendation_repository import RecommendationRepository


def test_active_replacements_map_returns_empty_dict_for_empty_list():
    db = MagicMock()
    repo = RecommendationRepository(db)

    result = repo.active_replacements_map([])

    assert result == {}
    db.query.assert_not_called()


def test_active_replacements_map_keeps_only_latest_per_trip_place():
    """같은 trip_place에 대해 여러 교체 기록이 있어도(정렬상 첫 행만) 가장 최근
    (applied_at desc, id desc) 한 건만 남아야 한다 — active_replacement()의 .first()와
    동일한 결과를 내야 한다."""
    db = MagicMock()
    tp1, tp2 = uuid4(), uuid4()
    latest_for_tp1 = MagicMock(trip_place_id=tp1)
    older_for_tp1 = MagicMock(trip_place_id=tp1)
    only_for_tp2 = MagicMock(trip_place_id=tp2)
    # DB가 이미 order_by(trip_place_id, applied_at desc, id desc)로 정렬해 반환한다고 가정
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        latest_for_tp1,
        older_for_tp1,
        only_for_tp2,
    ]
    repo = RecommendationRepository(db)

    result = repo.active_replacements_map([tp1, tp2])

    assert result == {tp1: latest_for_tp1, tp2: only_for_tp2}
