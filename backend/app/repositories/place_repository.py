"""places 테이블에 대한 SQLAlchemy 접근을 모아 둔 repository 이다."""
from uuid import UUID, uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models.place import Place


def _classify_district_code_backfill(
    current_area_cd: str | None,
    current_signgu_cd: str | None,
    new_area_cd: str | None,
    new_signgu_cd: str | None,
) -> str:
    """지역코드 백필 상태를 판정하는 순수 함수(DB 접근 없음) — 실행 경로와 미리보기 경로가
    같은 규칙을 쓰도록 공유한다.

    반환값: "missing_input"(새 값 자체가 불완전) / "conflict"(기존에 값이 있는 필드가 새
    값과 다름) / "unchanged"(이미 새 값과 같음) / "updated"(비어 있어서 채워야 함).
    """
    if not new_area_cd or not new_signgu_cd:
        return "missing_input"
    if current_area_cd and current_area_cd != new_area_cd:
        return "conflict"
    if current_signgu_cd and current_signgu_cd != new_signgu_cd:
        return "conflict"
    if current_area_cd and current_signgu_cd:
        return "unchanged"
    return "updated"


class PlaceRepository:
    """TourAPI 검색 결과를 내부 Place 로 get-or-create 하는 역할을 담당한다.

    ``create()``는 내부에서 커밋하지 않고 flush만 한다 — 호출자가 자신의 작업 단위 끝에서
    한 번만 commit()하도록(호출부: PlaceService, RecommendationService).
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, place_id: UUID) -> Place | None:
        return self.db.get(Place, place_id)

    def get_by_source(self, source_type: str, tour_content_id: str) -> Place | None:
        """같은 TourAPI 컨텐츠가 이미 저장돼 있으면 재사용하기 위한 조회."""
        if not tour_content_id:
            return None
        return (
            self.db.query(Place)
            .filter(Place.source_type == source_type, Place.tour_content_id == tour_content_id)
            .first()
        )

    def get_by_sources(
        self, pairs: list[tuple[str, str | None]]
    ) -> dict[tuple[str, str], Place]:
        """(source_type, tour_content_id) 여러 쌍을 한 번에 조회한다.

        get_by_source()를 후보 수만큼 반복 호출하면 STEP6처럼 후보가 여러 개일 때 그
        개수만큼 쿼리가 나간다 — (source_type, tour_content_id) UNIQUE 제약을 이용해
        IN 절 하나로 일괄 조회한다.
        """
        valid_pairs = [(source_type, cid) for source_type, cid in pairs if cid]
        if not valid_pairs:
            return {}
        rows = (
            self.db.query(Place)
            .filter(tuple_(Place.source_type, Place.tour_content_id).in_(valid_pairs))
            .all()
        )
        return {(row.source_type, row.tour_content_id): row for row in rows}

    def create(
        self,
        *,
        source_type: str,
        tour_content_id: str | None,
        region_id: int | None,
        name: str,
        longitude: float | None,
        latitude: float | None,
        is_recommendable: bool = True,
        expected_wait_minutes: int | None = None,
        address: str | None = None,
        area_cd: str | None = None,
        signgu_cd: str | None = None,
    ) -> Place:
        location = None
        if longitude is not None and latitude is not None:
            location = WKTElement(f"POINT({longitude} {latitude})", srid=4326)

        place = Place(
            source_type=source_type,
            tour_content_id=tour_content_id,
            region_id=region_id,
            name=name,
            location=location,
            is_recommendable=is_recommendable,
            expected_wait_minutes=expected_wait_minutes,
            address=address,
            area_cd=area_cd,
            signgu_cd=signgu_cd,
        )
        self.db.add(place)
        self.db.flush()
        self.db.refresh(place)
        return place

    def get_or_create(
        self,
        *,
        source_type: str,
        tour_content_id: str | None,
        name: str,
        longitude: float | None,
        latitude: float | None,
        region_id: int | None = None,
        is_recommendable: bool = True,
        area_cd: str | None = None,
        signgu_cd: str | None = None,
    ) -> Place:
        """외부 ID(tour_content_id) 기준 원자적 get-or-create.

        동시 요청 두 개가 같은 외부 관광지를 동시에 처음 조회하면 둘 다 "없음"을 볼 수 있어
        단순 SELECT-then-INSERT는 안전하지 않다. ``INSERT ... ON CONFLICT DO NOTHING``으로
        원자적으로 시도하고, 충돌로 반환 행이 없으면(다른 요청이 먼저 만듦) 그 행을 다시
        조회해서 돌려준다 — ``rollback()`` 없이(이 저장소의 다른 upsert 계열과 같은 패턴).
        Postgres는 이 INSERT가 충돌을 감지하기 전에 먼저 만든 트랜잭션의 커밋/롤백을
        기다리므로, 여기서 반환 행이 없다는 건 그 트랜잭션이 이미 커밋했다는 뜻이라
        곧바로 하는 재조회가 항상 그 행을 찾는다.

        ``tour_content_id``가 없는 custom 장소는 충돌 여지가 없으니 그냥 새로 만든다 —
        이름이 같아도 다른 사용자/장소와 절대 합쳐지지 않는다(이 경로 자체가 그 검사를 안 함).
        """
        tour_content_id = tour_content_id or None
        if not tour_content_id:
            return self.create(
                source_type=source_type,
                tour_content_id=None,
                region_id=region_id,
                name=name,
                longitude=longitude,
                latitude=latitude,
                is_recommendable=is_recommendable,
                area_cd=area_cd,
                signgu_cd=signgu_cd,
            )

        location = None
        if longitude is not None and latitude is not None:
            location = WKTElement(f"POINT({longitude} {latitude})", srid=4326)

        insert_stmt = pg_insert(Place).values(
            id=uuid4(),
            source_type=source_type,
            tour_content_id=tour_content_id,
            region_id=region_id,
            name=name,
            location=location,
            is_recommendable=is_recommendable,
            area_cd=area_cd,
            signgu_cd=signgu_cd,
        )
        stmt = insert_stmt.on_conflict_do_nothing(
            index_elements=["source_type", "tour_content_id"]
        ).returning(Place)
        place = self.db.execute(
            stmt, execution_options={"populate_existing": True}
        ).scalars().first()
        if place is None:
            # 충돌 — 다른 요청이 먼저 만든 기존 place. 이번 응답의 지역코드로 보충을 시도한다
            # (이 자리에서 처음 만든 place라면 이미 우리가 지정한 값 그대로라 보충이 필요 없다).
            place = self.get_by_source(source_type, tour_content_id)
            self.apply_district_code_backfill(place, area_cd, signgu_cd)
        self.db.flush()
        return place

    def apply_district_code_backfill(
        self, place: Place, area_cd: str | None, signgu_cd: str | None
    ) -> str:
        """행을 잠그고("SELECT ... FOR UPDATE") "지금" DB의 진짜 값으로 판정한 뒤에만 UPDATE한다.

        Python이 들고 있는 place 객체의 값은 이 메서드를 부르기 전에 로드된 스냅샷이라, 그
        사이 다른 세션이 먼저 채웠을 수 있다 — 그 스냅샷 기준으로 판정하면 상태가 부정확해질
        뿐 아니라, 최악의 경우 두 세션이 서로 다른 값으로 경합하는 lost-update가 생긴다.
        FOR UPDATE로 잠근 뒤 다시 읽은 값을 기준으로만 판정·기록한다.
        """
        if not area_cd or not signgu_cd:
            return "missing_input"

        # 컬럼만 골라서 Core select()로 조회한다(엔티티 전체를 query(Place)로 읽지 않음) —
        # SQLAlchemy는 query(Place)처럼 엔티티 전체를 조회할 때 이미 세션에 로드돼 있는 같은
        # PK의 객체가 있으면 기본적으로 그 객체를 재사용하고 속성을 덮어쓰지 않는다
        # (populate_existing=True를 줘야 갱신됨) — SELECT ... FOR UPDATE로 잠갔어도 이 함정에
        # 걸리면 이미 세션에 로드된 place 객체의 오래된 값을 그대로 보게 된다. 컬럼만 뽑는
        # select(Place.area_cd, Place.signgu_cd)는 ORM 엔티티/identity map을 전혀 안 거치고
        # 결과 행의 값을 그대로 돌려주므로 이 문제 자체가 없다 — 나중에 이 부분을
        # query(Place)... 형태로 바꾸게 되면 반드시 populate_existing=True를 같이 써야 한다.
        current_area_cd, current_signgu_cd = self.db.execute(
            select(Place.area_cd, Place.signgu_cd).where(Place.id == place.id).with_for_update()
        ).one()
        status = _classify_district_code_backfill(current_area_cd, current_signgu_cd, area_cd, signgu_cd)
        if status == "updated":
            self.db.execute(
                update(Place).where(Place.id == place.id).values(area_cd=area_cd, signgu_cd=signgu_cd)
            )
            place.area_cd = area_cd
            place.signgu_cd = signgu_cd
            self.db.flush()
        return status

    def preview_district_code_backfill(
        self, place_id: UUID, area_cd: str | None, signgu_cd: str | None
    ) -> str:
        """실제로 쓰지 않고 예상 결과만 돌려준다 — dry-run 전용, 잠금 없는 일반 조회."""
        current_area_cd, current_signgu_cd = self.db.execute(
            select(Place.area_cd, Place.signgu_cd).where(Place.id == place_id)
        ).one()
        return _classify_district_code_backfill(current_area_cd, current_signgu_cd, area_cd, signgu_cd)
