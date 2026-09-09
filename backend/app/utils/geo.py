"""장소 좌표 조회 유틸 (PostGIS ST_X/ST_Y, 실패 시 None)."""
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_place_coords(db: Session, place_id: UUID) -> tuple[float, float] | None:
    """(lat, lng) 반환. GEOGRAPHY 미지원/좌표 없으면 None."""
    try:
        row = db.execute(
            text(
                "SELECT ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng "
                "FROM place WHERE id = :id"
            ),
            {"id": str(place_id)},
        ).mappings().first()
    except Exception:
        db.rollback()
        return None
    if row is None or row["lat"] is None or row["lng"] is None:
        return None
    return float(row["lat"]), float(row["lng"])
