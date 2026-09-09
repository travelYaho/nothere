"""경험 태그(experience_tag) ORM — Part1."""
from sqlalchemy import Boolean, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExperienceTag(Base):
    __tablename__ = "experience_tag"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # ERD 원본엔 없는 필드. STEP2/방문목적 UI에 10종 태그를 일정한 순서로 노출하기 위한 추가 컬럼.
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
