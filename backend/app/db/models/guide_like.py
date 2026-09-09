"""공개 가이드북에 대한 좋아요 한 건을 저장하는 guide_like 모델이다.

비로그인 사용자의 좋아요는 지원하지 않는다(단순화). likeCount/isLikedByMe
는 이 테이블에서 매번 계산하며, share_link 자체에 카운트 컬럼을 두지
않는다 — 동기화가 어긋날 위험을 피하기 위해서다.
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.profile import Profile
    from app.db.models.share_link import ShareLink


class GuideLike(Base):
    """share_link 1건 + user 1명 조합의 좋아요를 저장하는 guide_like 모델."""
    __tablename__ = "guide_like"
    __table_args__ = (
        UniqueConstraint("share_link_id", "user_id", name="uq_guide_like_share_link_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    share_link_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("share_link.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    share_link: Mapped["ShareLink"] = relationship(back_populates="likes")
    user: Mapped["Profile"] = relationship()
