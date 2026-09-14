"""지역(region) ORM — Part1.

area_cd/signgu_cd는 팀 테스트(tests/db/test_models.py::test_region_matches_erd_exactly)가
region의 허용 컬럼으로 이미 명시하고 있어 그대로 둔다. 다만 region은 시/도 단위로 시드되어
있어(서울특별시/부산광역시) 집중률 API가 필요로 하는 구 단위 코드를 이 컬럼에 의미 있게
담을 수 없다 — 그래서 실제 분석 로직(app/domains/analysis/service.py)은 이 필드를 더 이상
읽지 않고 place.area_cd/signgu_cd(구 단위, TourAPI 응답 기준)를 쓴다.
"""
from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Region(Base):
    __tablename__ = "region"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    area_cd: Mapped[str | None] = mapped_column(String(20), nullable=True)
    signgu_cd: Mapped[str | None] = mapped_column(String(20), nullable=True)
