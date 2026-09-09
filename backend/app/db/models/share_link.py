"""가이드북 공유 링크(share_link) 모델이다.

Trip 을 외부에 공개하는 단위로, `token` 으로 비로그인 사용자도 조회할 수
있게 한다. `visibility` 는 링크를 아는 사람만(link) / 소유자만(private) /
누구나 탐색 목록에서 찾을 수 있음(public) 세 가지 값을 가진다.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.guide_like import GuideLike
    from app.db.models.trip import Trip


class ShareLinkVisibility:
    """visibility 컬럼이 가질 수 있는 값 모음."""
    LINK = "link"
    PRIVATE = "private"
    PUBLIC = "public"

    ALL = (LINK, PRIVATE, PUBLIC)


class ShareLink(Base):
    """Trip 1건을 공유 링크로 노출하는 share_link 모델."""
    __tablename__ = "share_link"
    __table_args__ = (
        CheckConstraint(
            "visibility in ('link', 'private', 'public')",
            name="ck_share_link_visibility",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ShareLinkVisibility.LINK
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    trip: Mapped["Trip"] = relationship()
    likes: Mapped[list["GuideLike"]] = relationship(
        back_populates="share_link",
        cascade="all, delete-orphan",
    )
