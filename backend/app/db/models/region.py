"""지역(region) ORM — Part1."""
from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Region(Base):
    __tablename__ = "region"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 집중률 API(공공데이터포털 TatsCnctrRateService)의 지역 코드. 매핑이 아직 없는 지역은 NULL.
    area_cd: Mapped[str | None] = mapped_column(String(20), nullable=True)
    signgu_cd: Mapped[str | None] = mapped_column(String(20), nullable=True)
