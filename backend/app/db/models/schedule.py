"""일정(schedules) ORM 모델이다.

소유자(user_id) 기준으로 조회·수정하며, 장소는 schedule_places 로 연결한다.
"""
import enum
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.profile import Profile
    from app.db.models.schedule_place import SchedulePlace


class ScheduleStatus(str, enum.Enum):
    """일정 상태값 모음."""
    DRAFT = "DRAFT"
    ANALYZED = "ANALYZED"
    EDITING = "EDITING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"


IN_PROGRESS_STATUSES = (
    ScheduleStatus.DRAFT.value,
    ScheduleStatus.ANALYZED.value,
    ScheduleStatus.EDITING.value,
)


class Schedule(Base):
    """로그인 사용자 소유의 여행 일정."""
    __tablename__ = "schedules"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    travel_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    region_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ScheduleStatus.DRAFT.value,
    )
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

    user: Mapped["Profile"] = relationship(back_populates="schedules")
    places: Mapped[list["SchedulePlace"]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
        order_by="SchedulePlace.order_index",
    )
