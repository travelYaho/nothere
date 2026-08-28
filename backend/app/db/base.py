"""SQLAlchemy ORM 모델들이 공통으로 상속하는 Declarative Base 이다."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 테이블 모델의 메타데이터를 모아 Alembic 이 추적할 수 있게 한다."""
    pass
