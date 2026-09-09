"""가이드북에 곁들이는 사용자 콘텐츠(그림일기 등)를 저장하는 guide_entry 모델이다.

`is_public` 은 share_link.visibility 와는 다른 층위의 공개 여부다 — 일정
자체는 공개 갤러리에 노출되더라도, 그림일기처럼 개인 기록 성격이 강한
콘텐츠는 작성자가 별도로 공개 동의한 것만(is_public=true) 갤러리 카드
대표 이미지 등으로 사용한다.
"""
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.trip import Trip, TripPlace


class GuideEntry(Base):
    """Trip 에 딸린 그림일기/메모 한 건을 저장하는 guide_entry 모델."""
    __tablename__ = "guide_entry"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trip_place_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_places.id", ondelete="SET NULL"),
        nullable=True,
    )
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    trip: Mapped["Trip"] = relationship()
    trip_place: Mapped["TripPlace | None"] = relationship()
