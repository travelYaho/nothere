"""places 테이블에 대한 SQLAlchemy 접근을 모아 둔 repository 이다."""
from uuid import UUID, uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy import or_, select, tuple_, update
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

    def get_by_ids(self, place_ids: list[UUID]) -> dict[UUID, Place]:
        """여러 place_id를 한 번에 조회한다. 가이드북 조립(build_guide)이 정류장·교체 전
        장소를 건마다 get_by_id()로 조회하면 그만큼 DB 왕복이 났다 — IN 절 하나로 모은다.
        """
        if not place_ids:
            return {}
        rows = self.db.query(Place).filter(Place.id.in_(place_ids)).all()
        return {row.id: row for row in rows}

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
        address: str | None = None,
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
                address=address,
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
            address=address,
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
            # 충돌 — 다른 요청이 먼저 만든 기존 place. 이번 응답의 지역코드·주소로 보충을
            # 시도한다(이 자리에서 처음 만든 place라면 이미 우리가 지정한 값 그대로라
            # 보충이 필요 없다).
            place = self.get_by_source(source_type, tour_content_id)
            self.apply_district_code_backfill(place, area_cd, signgu_cd)
            self.backfill_address_if_missing(place, address)
        self.db.flush()
        return place

    def get_or_create_many(
        self,
        *,
        source_type: str,
        region_id: int | None,
        items: list[dict],
    ) -> dict[str, Place]:
        """tour_content_id가 있는 검색 결과 여러 건을 한 번에 get-or-create한다.

        get_or_create()를 결과 건수만큼(검색 결과 최대 20건) 반복 호출하면 그만큼 DB
        왕복이 쌓인다 — analysis_repository.bulk_upsert_spots()가 STEP4에서 같은 문제를
        겪고 쓴 해법(일괄 INSERT ON CONFLICT DO NOTHING → 남은 건만 재조회)을 그대로
        적용한다. tour_content_id가 없는 항목(충돌 대상이 없는 custom 성격)은 호출부가
        create()로 개별 처리해야 한다 — 여기 items에 넣지 않는다.

        반환값은 tour_content_id -> Place. 새로 삽입된 place는 이번 area_cd/signgu_cd
        그대로라 보충이 필요 없고, 기존에 있던(=이번에 처음 만든 게 아닌) place에만
        apply_district_code_backfill()을 시도한다 — get_or_create() 단건 경로와 동일한 규칙.
        """
        if not items:
            return {}

        by_cid = {item["tour_content_id"]: item for item in items}
        existing = self.get_by_sources([(source_type, cid) for cid in by_cid])
        existing_by_cid = {cid: place for (_, cid), place in existing.items()}

        to_insert = [item for cid, item in by_cid.items() if cid not in existing_by_cid]
        inserted_by_cid: dict[str, Place] = {}
        if to_insert:
            values = []
            for item in to_insert:
                longitude, latitude = item["longitude"], item["latitude"]
                location = (
                    WKTElement(f"POINT({longitude} {latitude})", srid=4326)
                    if longitude is not None and latitude is not None
                    else None
                )
                values.append(
                    {
                        "id": uuid4(),
                        "source_type": source_type,
                        "tour_content_id": item["tour_content_id"],
                        "region_id": region_id,
                        "name": item["name"],
                        "location": location,
                        "address": item.get("address"),
                        "area_cd": item["area_cd"],
                        "signgu_cd": item["signgu_cd"],
                    }
                )
            stmt = pg_insert(Place).values(values).on_conflict_do_nothing(
                index_elements=["source_type", "tour_content_id"]
            ).returning(Place)
            inserted = self.db.execute(
                stmt, execution_options={"populate_existing": True}
            ).scalars().all()
            inserted_by_cid = {place.tour_content_id: place for place in inserted}

        # 위 INSERT와 최초 조회 사이에 다른 세션이 같은 content_id를 먼저 커밋하면
        # ON CONFLICT DO NOTHING이 그 건만 조용히 건너뛴다 — 남은 건만 다시 조회한다.
        raced_cids = [cid for cid in by_cid if cid not in existing_by_cid and cid not in inserted_by_cid]
        raced_by_cid: dict[str, Place] = {}
        if raced_cids:
            raced = self.get_by_sources([(source_type, cid) for cid in raced_cids])
            raced_by_cid = {cid: place for (_, cid), place in raced.items()}

        found = {**existing_by_cid, **raced_by_cid}
        self.apply_district_code_backfill_many(
            [(place, by_cid[cid]["area_cd"], by_cid[cid]["signgu_cd"]) for cid, place in found.items()]
        )
        for cid, place in found.items():
            self.backfill_address_if_missing(place, by_cid[cid].get("address"))

        self.db.flush()
        return {**existing_by_cid, **inserted_by_cid, **raced_by_cid}

    def backfill_address_if_missing(self, place: Place, address: str | None) -> str:
        """기존 place의 주소가 비어 있을 때만, 조건부 UPDATE로 안전하게 보충한다.

        지역코드 백필(``apply_district_code_backfill``)과 달리 주소는 "충돌 판정"이
        필요 없다 — 조건이 "비어 있으면 채움" 하나뿐이라 사전에 ``SELECT ... FOR UPDATE``로
        잠그고 판정할 필요가 없다. 다만 이 말이 "잠금이 전혀 없다"는 뜻은 아니다 —
        ``UPDATE ... WHERE`` 문장 자체가 대상 행을 잠그고 실행되므로, 동시에 두 요청이
        이 메서드를 불러도 그중 하나만 실제로 반영된다.

        그래서 UPDATE가 실제로 몇 행을 바꿨는지를 ``RETURNING``으로 반드시 확인한 뒤에만
        메모리의 ``place`` 객체를 갱신해야 한다 — 다른 요청이 먼저 채웠다면 이 UPDATE는
        0행을 바꾸고, 그 경우 내가 보낸 입력값을 그냥 ``place.address``에 대입하면 메모리와
        DB가 어긋나 이후 flush 때 방금 다른 요청이 커밋한 진짜 주소를 내 입력값으로 도로
        덮어쓸 위험이 있다(2026-09-17, CodeRabbit 리뷰로 발견).

        0행이어도 ``place.address``를 그대로 방치하면 안 된다 — 호출 전에 이미 메모리에
        올라온 ``place`` 객체의 ``address``는 그 시점의 스냅샷(예: 비어 있던 상태)일 수
        있고, 그 사이 다른 세션이 실제로 채웠을 수 있다. 그러면 이 메서드가 끝난 뒤에도
        호출자는 여전히 "주소 없음"이라는 오래된 값을 들고 있게 된다 — 덮어쓰기를 막는 것과
        반환 객체를 최신 상태로 맞추는 것은 별개 문제라, 0행이면 ``refresh``로 실제 DB
        값을 다시 읽어와야 한다(2026-09-17, 코드 리뷰로 추가 발견).

        "비어 있음" 판정은 NULL뿐 아니라 공백 문자(스페이스·탭·개행 등)만 있는 값도
        포함한다 — Postgres 기본 ``TRIM()``은 스페이스만 제거해 탭/개행만 있는 값을 못
        잡으므로 정규식(``~ '^\\s*$'``)으로 판정한다. 이 정규화(``strip()``)는 **이
        보충 경로에만** 적용된다 — 신규 생성 경로(``create()``/이 메서드 위의 INSERT)는
        전달받은 주소를 그대로 저장하므로, "쓰기·읽기 전체가 통일됐다"는 뜻은 아니다.
        """
        normalized = address.strip() if address else None
        if not normalized:
            return "no_input"
        row = self.db.execute(
            update(Place)
            .where(
                Place.id == place.id,
                or_(Place.address.is_(None), Place.address.op("~")(r"^\s*$")),
            )
            .values(address=normalized)
            .returning(Place.address)
        ).first()
        if row is None:
            self.db.refresh(place, attribute_names=["address"])
            return "not_empty"
        place.address = row[0]
        self.db.flush()
        return "updated"

    def apply_district_code_backfill_many(
        self, items: list[tuple[Place, str | None, str | None]]
    ) -> None:
        """apply_district_code_backfill()을 대상 수만큼 반복하면, 값이 이미 일치해서
        UPDATE가 필요 없는 경우조차 매번 ``SELECT ... FOR UPDATE``로 잠그고 읽는다 —
        get_or_create_many()가 검색 결과 대부분(이미 알던 장소)에 이걸 반복하면 건수만큼
        잠금 조회가 나가 N+1 제거 효과가 깎인다(코드 리뷰로 발견). 잠금 조회만 IN 절
        하나로 묶고, 실제 갱신이 필요한(드문) 건만 개별 UPDATE로 반영한다.
        """
        candidates = [(place, area_cd, signgu_cd) for place, area_cd, signgu_cd in items if area_cd and signgu_cd]
        if not candidates:
            return

        ids = [place.id for place, _, _ in candidates]
        current_by_id = {
            row.id: (row.area_cd, row.signgu_cd)
            for row in self.db.execute(
                select(Place.id, Place.area_cd, Place.signgu_cd)
                .where(Place.id.in_(ids))
                .with_for_update()
            )
        }
        for place, area_cd, signgu_cd in candidates:
            current_area_cd, current_signgu_cd = current_by_id.get(place.id, (None, None))
            status = _classify_district_code_backfill(current_area_cd, current_signgu_cd, area_cd, signgu_cd)
            if status == "updated":
                self.db.execute(
                    update(Place).where(Place.id == place.id).values(area_cd=area_cd, signgu_cd=signgu_cd)
                )
                place.area_cd = area_cd
                place.signgu_cd = signgu_cd
        self.db.flush()

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
