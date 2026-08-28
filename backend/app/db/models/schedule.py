"""홈 화면 요약 조회에 쓰는 최소 일정 모델이다.

Supabase 가 DB 를 호스팅하더라도, FastAPI 가 직접 조회할 테이블 구조는 ORM 으로 정의해야 한다.
"""
# [1주차 범위] 일정 CRUD·장소 등록·분석·추천은 구현하지 않는다.
# GET /api/home 의 draftSchedule/recentSchedules 요약을 위해 최소 스키마만 둔다.
# GET/DELETE /api/schedules* 는 이후 담당자가 구현한다.
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


class ScheduleStatus(str, enum.Enum):
    """홈 요약에서 구분하는 최소 일정 상태값 모음."""
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
    """로그인 사용자 소유의 일정 요약 정보를 저장하는 schedules 모델."""
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
