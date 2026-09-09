"""TourAPI 기준 장소(place) ORM. location 은 PostGIS GEOGRAPHY.

`expected_wait_minutes`/`address` 는 ERD 원본엔 없는 필드다. "장소 직접
추가"(Figma node 48:3842) 로 등록하는 커스텀 장소는 집중도 분석 대상이 아니라서
(is_recommendable=False) 사용자가 직접 예상 대기시간을 입력하게 되어 있고, 그
값을 저장할 곳이 필요해 추가했다. 주소도 카카오 지오코딩("카카오맵" 제품
비활성화로 당장 불가)이 가능해지기 전까지는 텍스트로만 저장해 둔다.
"""
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.db.base import Base


class Geography(UserDefinedType):
    """PostGIS GEOGRAPHY 컬럼용 최소 타입."""

    cache_ok = True

    def get_col_spec(self, **_kwargs: Any) -> str:
        return "GEOGRAPHY(POINT,4326)"


class Place(Base):
    __tablename__ = "place"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tour_content_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    region_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("region.id"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[Any | None] = mapped_column(Geography, nullable=True)
    is_recommendable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expected_wait_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
