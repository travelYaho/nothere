"""가이드북 사용자 콘텐츠(guide_entry) ORM — Part3.

`is_public` 은 share_link.visibility 와는 다른 층위의 공개 여부다 — 일정
자체는 공개 갤러리에 노출되더라도, 그림일기처럼 개인 기록 성격이 강한
콘텐츠는 작성자가 별도로 공개 동의한 것만(is_public=true) 갤러리 카드
대표 이미지 등으로 사용한다.
"""
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GuideEntry(Base):
    __tablename__ = "guide_entry"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trip_place_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_place.id", ondelete="SET NULL"),
        nullable=True,
    )
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
