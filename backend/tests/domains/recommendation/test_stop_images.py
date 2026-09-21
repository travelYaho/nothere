"""가이드북 정류장 썸네일 동시 조회(_resolve_stop_images) 테스트."""
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.domains.recommendation import service as service_module
from app.domains.recommendation.service import RecommendationService


def _place(content_id, name="장소"):
    return SimpleNamespace(tour_content_id=content_id, name=name)


def _slow_image(delay):
    def fetch(content_id):
        time.sleep(delay)
        return f"https://img.example/{content_id}.jpg"

    return fetch


def test_stop_images_are_fetched_concurrently_in_order():
    svc = RecommendationService(MagicMock())
    places = [_place(str(i)) for i in range(4)]

    with patch.object(service_module.tour_api, "fetch_place_image", side_effect=_slow_image(0.3)):
        started = time.monotonic()
        images = svc._resolve_stop_images(places)
        elapsed = time.monotonic() - started

    assert images == [f"https://img.example/{i}.jpg" for i in range(4)]
    assert elapsed < 0.9  # 순차면 1.2s 이상


def test_missing_place_and_failed_fetch_become_none():
    svc = RecommendationService(MagicMock())

    def fetch(content_id):
        raise RuntimeError("boom")

    with patch.object(service_module.tour_api, "fetch_place_image", side_effect=fetch):
        assert svc._resolve_stop_images([None, _place("1")]) == [None, None]


def test_slow_fetch_past_deadline_is_dropped(monkeypatch):
    monkeypatch.setattr(service_module, "_STOP_IMAGE_DEADLINE_SECONDS", 0.2)
    svc = RecommendationService(MagicMock())

    with patch.object(service_module.tour_api, "fetch_place_image", side_effect=_slow_image(1.0)):
        started = time.monotonic()
        images = svc._resolve_stop_images([_place("1")])
        elapsed = time.monotonic() - started

    assert images == [None]
    assert elapsed < 0.6
