"""여행 일정(Trip) 및 하위 장소(TripPlace) 도메인 모델이다.

1주차 플레이스홀더였던 Schedule 을 대체한다. STEP2(조건입력)~STEP9(가이드북)
전체가 이 Trip/TripPlace 를 축으로 동작하므로, 스키마 문서(파트1) 필드는
그대로 두고 홈 화면 정렬에 필요한 updated_at 만 실무적으로 추가했다.
"""
import enum
from datetime import date, datetime, time
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.experience_tag import ExperienceTag
    from app.db.models.place import Place
    from app.db.models.profile import Profile
    from app.db.models.region import Region


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
    """로그인 사용자 소유의 여행 일정을 저장하는 trips 모델."""
    __tablename__ = "trips"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    region_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("regions.id", ondelete="RESTRICT"),
        nullable=False,
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

    user: Mapped["Profile"] = relationship(back_populates="trips")
    region: Mapped["Region"] = relationship(back_populates="trips")
    preferred_experiences: Mapped[list["TripPreferredExperience"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
    )
    trip_places: Mapped[list["TripPlace"]] = relationship(
        back_populates="trip",
        foreign_keys="TripPlace.trip_id",
        cascade="all, delete-orphan",
        order_by="TripPlace.position",
    )


class TripPreferredExperience(Base):
    """STEP2 에서 선택한 선호 경험(1~3순위, 가중치 1.0/0.7/0.5)을 저장한다."""
    __tablename__ = "trip_preferred_experiences"

    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        primary_key=True,
    )
    experience_tag_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("experience_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weight: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)

    trip: Mapped["Trip"] = relationship(back_populates="preferred_experiences")
    experience_tag: Mapped["ExperienceTag"] = relationship(back_populates="trip_preferences")


class TripPlace(Base):
    """Trip 에 등록된 장소(순서/방문시간/체류시간/고정여부)를 저장하는 trip_places 모델."""
    __tablename__ = "trip_places"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trip_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    initial_place_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("places.id", ondelete="SET NULL"),
        nullable=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    visit_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    stay_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=60)
    is_fixed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # ERD 원본엔 없는 필드. 생성/수정 시각 추적용으로 실무적으로 추가했다.
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

    trip: Mapped["Trip"] = relationship(back_populates="trip_places", foreign_keys=[trip_id])
    place: Mapped["Place"] = relationship(back_populates="trip_places", foreign_keys=[place_id])
    initial_place: Mapped["Place | None"] = relationship(foreign_keys=[initial_place_id])
    purposes: Mapped[list["TripPlacePurpose"]] = relationship(
        back_populates="trip_place",
        cascade="all, delete-orphan",
    )


class TripPlacePurpose(Base):
    """방문 목적 태그(다중선택, 0개 이상)를 저장하는 trip_place_purposes 모델."""
    __tablename__ = "trip_place_purposes"

    trip_place_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("trip_places.id", ondelete="CASCADE"),
        primary_key=True,
    )
    purpose_tag_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("experience_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    trip_place: Mapped["TripPlace"] = relationship(back_populates="purposes")
    purpose_tag: Mapped["ExperienceTag"] = relationship(back_populates="trip_place_purposes")
