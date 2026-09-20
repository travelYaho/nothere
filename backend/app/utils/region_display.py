"""가이드북 표지에 쓸 시·구 표시명을 주소/지역명에서 뽑는다."""
from __future__ import annotations

import re
from collections import Counter

_CITY_SUFFIX = re.compile(r"(특별자치시|특별자치도|광역시|특별시|자치시|자치도)$")
_DISTRICT_RE = re.compile(r"([가-힣]+(?:구|군))")


def short_city_name(region_name: str | None) -> str | None:
    """'서울특별시' → '서울', '서울 종로구' → '서울'."""
    if not region_name or not region_name.strip():
        return None
    first = region_name.strip().split()[0]
    stripped = _CITY_SUFFIX.sub("", first)
    return stripped or first


def district_from_text(text: str | None) -> str | None:
    """주소나 지역명에서 첫 구/군을 찾는다. '서울특별시 종로구 …' → '종로구'."""
    if not text:
        return None
    match = _DISTRICT_RE.search(text)
    return match.group(1) if match else None


def majority_district(texts: list[str | None]) -> str | None:
    """여러 주소에서 가장 많이 나온 구/군. 동률이면 먼저 등장한 쪽."""
    names = [district_from_text(text) for text in texts]
    counted = [name for name in names if name]
    if not counted:
        return None
    return Counter(counted).most_common(1)[0][0]
