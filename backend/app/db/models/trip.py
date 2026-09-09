"""여행 일정(Trip) 도메인 모델이다.

1주차 플레이스홀더였던 Schedule 을 대체한다. STEP2(조건입력)~STEP9(가이드북)
전체가 이 Trip 을 축으로 동작하므로, 스키마 문서(파트1) 필드는 그대로 두고
홈 화면 정렬에 필요한 updated_at 만 실무적으로 추가했다.
"""
import enum
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.preference import TripPreferredExperience
    from app.db.models.region import Region
    from app.db.models.trip_place import TripPlace


class TripStatus(str, enum.Enum):
    """Trip 의 진행 상태값 모음."""
    DRAFT = "draft"
    ANALYZED = "analyzed"
    EDITING = "editing"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"


IN_PROGRESS_STATUSES = (
    TripStatus.DRAFT.value,
    TripStatus.ANALYZED.value,
    TripStatus.EDITING.value,
)


class Trip(Base):
    __tablename__ = "trip"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profile.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    region_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("region.id"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    travel_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    companion_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transport_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extra_time_limit_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TripStatus.DRAFT.value)
    current_step: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    needs_reanalysis: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # ERD 원본엔 없는 필드. 홈 화면의 "진행 중 일정" 최신순 정렬(TripRepository)에 필요해 추가했다.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    region: Mapped["Region | None"] = relationship()
    preferred_experiences: Mapped[list["TripPreferredExperience"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    trip_places: Mapped[list["TripPlace"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripPlace.position",
    )
