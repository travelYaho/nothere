"""RouteService.get_legs() 배치 조회를 검증한다.

get_leg()를 구간 수만큼 반복하던 걸 배치로 바꾼 게 이번 변경의 핵심이라, 캐시 히트/미스
경로 각각에서 DB/외부 API 호출이 예상대로(구간 수와 무관하게) 나가는지에 집중한다.
"""
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.clients.kakao_mobility import RouteResult
from app.domains.recommendation.route import RouteService


def _service():
    db = MagicMock()
    client = MagicMock()
    return RouteService(db, client=client), db, client


def test_get_legs_returns_empty_dict_for_empty_pairs():
    svc, db, client = _service()

    result = svc.get_legs([], "walk")

    assert result == {}
    db.query.assert_not_called()
    client.directions.assert_not_called()


def test_get_legs_all_cached_makes_one_query_and_no_external_calls():
    svc, db, client = _service()
    p1, p2, p3 = uuid4(), uuid4(), uuid4()
    cached_row = MagicMock(distance_m=100, duration_seconds=60, provider="haversine", is_estimated=True)
    svc._get_cache_many = MagicMock(return_value={(p1, p2): cached_row, (p2, p3): cached_row})

    result = svc.get_legs([(p1, p2), (p2, p3)], "walk")

    assert set(result.keys()) == {(p1, p2), (p2, p3)}
    svc._get_cache_many.assert_called_once()
    client.directions.assert_not_called()
    db.query.assert_not_called()  # _put_cache 등 추가 DB 접근 없음


def test_get_legs_cache_miss_fetches_coords_once_and_resolves_leg():
    svc, db, client = _service()
    origin, dest = uuid4(), uuid4()
    svc._get_cache_many = MagicMock(return_value={})
    svc._put_cache = MagicMock()

    with patch(
        "app.domains.recommendation.route.get_place_coords_map",
        return_value={str(origin): (37.5, 127.0), str(dest): (37.6, 127.1)},
    ) as mock_coords_map:
        result = svc.get_legs([(origin, dest)], "walk")

    mock_coords_map.assert_called_once()
    assert (origin, dest) in result
    svc._put_cache.assert_called_once()


def test_get_legs_skips_pair_when_coords_missing():
    svc, db, client = _service()
    origin, dest = uuid4(), uuid4()
    svc._get_cache_many = MagicMock(return_value={})
    svc._put_cache = MagicMock()

    with patch(
        "app.domains.recommendation.route.get_place_coords_map",
        return_value={str(origin): (37.5, 127.0)},  # dest 좌표 없음
    ):
        result = svc.get_legs([(origin, dest)], "walk")

    assert result == {}
    svc._put_cache.assert_not_called()


def test_get_legs_deduplicates_repeated_pairs():
    svc, db, client = _service()
    p1, p2 = uuid4(), uuid4()
    svc._get_cache_many = MagicMock(return_value={})
    svc._put_cache = MagicMock()

    with patch(
        "app.domains.recommendation.route.get_place_coords_map",
        return_value={str(p1): (37.5, 127.0), str(p2): (37.6, 127.1)},
    ):
        svc.get_legs([(p1, p2), (p1, p2)], "walk")

    called_pairs = svc._get_cache_many.call_args[0][0]
    assert called_pairs == [(p1, p2)]  # 중복 제거되어 한 번만 조회
