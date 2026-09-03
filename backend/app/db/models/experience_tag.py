"""선호 경험 태그(10종 고정) 기준 정보를 저장하는 experience_tags 모델이다.

Trip(선호경험), Place(장소 태그), TripPlace(방문목적)에서 전부 이 테이블을
공유 참조하므로, 코드 값 자체는 기획 확정 전까지 잠정치임을 시드 스크립트에
남겨 둔다.
"""
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.place import PlaceExperienceTag
    from app.db.models.trip import TripPlacePurpose, TripPreferredExperience
    from app.db.models.user_preference import UserLongTermPreference


class ExperienceTag(Base):
    """선호 경험/방문 목적 선택에 공통으로 쓰이는 experience_tags 모델."""
    __tablename__ = "experience_tags"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # ERD 원본엔 없는 필드. 10종 태그를 화면에 일정한 순서로 노출하기 위한 추가 컬럼.
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    place_tags: Mapped[list["PlaceExperienceTag"]] = relationship(back_populates="experience_tag")
    trip_preferences: Mapped[list["TripPreferredExperience"]] = relationship(
        back_populates="experience_tag"
    )
    trip_place_purposes: Mapped[list["TripPlacePurpose"]] = relationship(
        back_populates="purpose_tag"
    )
    user_long_term_preferences: Mapped[list["UserLongTermPreference"]] = relationship(
        back_populates="experience_tag"
    )
