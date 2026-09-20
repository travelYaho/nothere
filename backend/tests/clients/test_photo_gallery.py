"""PhotoGalleryService2 클라이언트가 실패해도 빈 결과를 내는지 검증한다."""
import httpx

from app.clients import photo_gallery
from app.core.config import settings


def test_search_image_urls_parses_gallery_items(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _fake_get(*args, **kwargs):
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "0000"},
                    "body": {
                        "totalCount": 2,
                        "items": {
                            "item": [
                                {"galWebImageUrl": "https://img.example/a.jpg"},
                                {"galWebImageUrl": "https://img.example/b.jpg"},
                            ]
                        },
                    },
                }
            },
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)

    assert photo_gallery.search_image_urls("서울 종로구") == [
        "https://img.example/a.jpg",
        "https://img.example/b.jpg",
    ]


def test_search_image_urls_calls_photo_gallery_service1(monkeypatch):
    monkeypatch.setattr(settings, "PHOTO_GALLERY_API_KEY", "gallery-key")
    monkeypatch.setattr(settings, "TOUR_API_KEY", "tour-key")
    captured: dict = {}

    def _fake_get(url, params=None, **kwargs):
        captured["url"] = url
        captured["serviceKey"] = (params or {}).get("serviceKey")
        return httpx.Response(
            200,
            json={"response": {"header": {"resultCode": "0000"}, "body": {"totalCount": 0}}},
            request=httpx.Request("GET", "https://example.com"),
        )

    monkeypatch.setattr(httpx, "get", _fake_get)
    photo_gallery.search_image_urls("서울")
    assert captured["url"].endswith("/PhotoGalleryService1/gallerySearchList1")
    assert captured["serviceKey"] == "gallery-key"


def test_first_image_for_place_retries_without_parentheses(monkeypatch):
    monkeypatch.setattr(settings, "PHOTO_GALLERY_API_KEY", "gallery-key")
    keywords: list[str] = []

    def _search(keyword, **kwargs):
        keywords.append(keyword)
        if keyword == "경국사":
            return ["https://img.example/temple.jpg"]
        return []

    monkeypatch.setattr(photo_gallery, "search_image_urls", _search)
    assert photo_gallery.first_image_for_place("경국사(서울)") == "https://img.example/temple.jpg"
    assert keywords == ["경국사(서울)", "경국사"]


def test_search_image_urls_returns_empty_on_network_error(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", _raise)

    assert photo_gallery.search_image_urls("서울") == []


def test_pick_cover_image_returns_random_choice(monkeypatch):
    monkeypatch.setattr(settings, "TOUR_API_KEY", "dummy-key")
    monkeypatch.setattr(
        photo_gallery,
        "search_image_urls",
        lambda keyword, **kwargs: ["https://img.example/a.jpg", "https://img.example/b.jpg"],
    )
    monkeypatch.setattr(photo_gallery.random, "choice", lambda urls: urls[0])

    assert photo_gallery.pick_cover_image("서울", "종로구") == "https://img.example/a.jpg"


def test_pick_cover_image_without_keyword_skips_network(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("키워드가 없으면 호출하면 안 된다")

    monkeypatch.setattr(photo_gallery, "search_image_urls", _fail)

    assert photo_gallery.pick_cover_image(None, None) is None
