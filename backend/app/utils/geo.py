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


def get_place_coords_map(db: Session, place_ids: list[UUID]) -> dict[str, tuple[float, float]]:
    """여러 place_id의 좌표를 한 번에 조회한다(가이드북 구간 여러 개를 한 번에 풀 때 씀).

    get_place_coords()를 장소 수만큼 반복하면 그만큼 DB 왕복이 나서, WHERE id = ANY(:ids)로
    한 번에 모아 온다. 반환 키는 UUID가 아니라 str이다 — 드라이버가 원시 SQL의 id 컬럼을
    uuid.UUID로 캐스팅해준다는 보장이 없어(register_uuid() 여부에 좌우됨) id::text로 직접
    캐스팅해 받는다. 호출부는 str(place_id)로 조회해야 한다.
    """
    if not place_ids:
        return {}
    try:
        rows = (
            db.execute(
                text(
                    "SELECT id::text AS id, ST_Y(location::geometry) AS lat, "
                    "ST_X(location::geometry) AS lng FROM place WHERE id = ANY(:ids)"
                ),
                {"ids": [str(pid) for pid in place_ids]},
            )
            .mappings()
            .all()
        )
    except Exception:
        db.rollback()
        return {}
    return {
        row["id"]: (float(row["lat"]), float(row["lng"]))
        for row in rows
        if row["lat"] is not None and row["lng"] is not None
    }
