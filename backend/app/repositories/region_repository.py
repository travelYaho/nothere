"""regions 테이블에 대한 SQLAlchemy 접근을 모아 둔 repository 이다."""
from sqlalchemy.orm import Session

from app.db.models.region import Region


class RegionRepository:
    """MVP 지원 지역(is_supported=true) 조회를 담당한다."""
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_supported(self) -> list[Region]:
        """STEP2 지역 선택 목록으로 노출할 지역만 id 순으로 반환한다."""
        return (
            self.db.query(Region)
            .filter(Region.is_supported.is_(True))
            .order_by(Region.id)
            .all()
        )

    def get_supported_by_id(self, region_id: int) -> Region | None:
        """Trip 생성 시 region_id 유효성 검사에 쓰는 단건 조회."""
        return (
            self.db.query(Region)
            .filter(Region.id == region_id, Region.is_supported.is_(True))
            .first()
        )
