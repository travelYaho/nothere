"""시·구 표시명 파싱."""
from app.utils.region_display import district_from_text, majority_district, short_city_name


def test_short_city_name_strips_suffixes():
    assert short_city_name("서울특별시") == "서울"
    assert short_city_name("부산광역시") == "부산"
    assert short_city_name("서울 종로구") == "서울"
    assert short_city_name(None) is None


def test_district_from_address():
    assert district_from_text("서울특별시 종로구 자하문로 15") == "종로구"
    assert district_from_text("부산광역시 해운대구 우동") == "해운대구"
    assert district_from_text("서울 종로구") == "종로구"
    assert district_from_text("주소 없음") is None


def test_majority_district_picks_most_common():
    assert (
        majority_district(
            [
                "서울특별시 종로구 자하문로",
                "서울특별시 종로구 통인동",
                "서울특별시 중구 명동",
            ]
        )
        == "종로구"
    )
    assert majority_district([]) is None
