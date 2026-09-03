"""사용자 장기 선호도(로드맵 기능용) 를 저장하는 user_long_term_preferences 모델이다."""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, SmallInteger, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experience_tag import ExperienceTag
    from app.db.models.profile import Profile


class UserLongTermPreference(Base):
    """사용자별 경험 태그 누적 선호 점수를 저장하는 모델(로드맵)."""
    __tablename__ = "user_long_term_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "experience_tag_id", name="uq_user_long_term_preference"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    experience_tag_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("experience_tags.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    trip_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["Profile"] = relationship(back_populates="long_term_preferences")
    experience_tag: Mapped["ExperienceTag"] = relationship(
        back_populates="user_long_term_preferences"
    )
