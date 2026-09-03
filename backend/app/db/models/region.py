"""여행 지역(서울/부산 등) 기준 정보를 저장하는 regions 모델이다.

스키마 문서(파트1) 기준 필드만 둔다. TourAPI/집중률 API 코드 매핑은
Place(source_type/tour_content_id), Part2 소유 concentration_spot 테이블이
각자 담당하므로 여기서는 중복 저장하지 않는다.
"""
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.place import Place
    from app.db.models.trip import Trip


class Region(Base):
    """MVP 지원 지역 목록을 관리하는 regions 모델."""
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    trips: Mapped[list["Trip"]] = relationship(back_populates="region")
    places: Mapped[list["Place"]] = relationship(back_populates="region")
