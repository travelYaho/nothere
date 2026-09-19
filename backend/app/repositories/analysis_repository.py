"""집중도 분석(STEP4) 관련 조회/저장. 소유권은 항상 부모 Trip.user_id로 확인한다."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload

from app.db.models.concentration import ConcentrationSpot, PlaceConcentrationMapping
from app.db.models.place import Place
from app.db.models.recommendation import TripPlaceAnalysis
from app.db.models.replacement import Replacement
from app.db.models.trip import Trip

_HUMAN_REVIEWED_STATUSES = {"approved", "rejected"}


class AnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_trip_owned(self, trip_id: UUID, user_id: UUID) -> Trip | None:
        return (
            self.db.query(Trip)
            .options(joinedload(Trip.trip_places))
            .filter(Trip.id == trip_id, Trip.user_id == user_id)
            .first()
        )

    def get_places_map(self, place_ids: list[UUID]) -> dict[UUID, Place]:
        if not place_ids:
            return {}
        rows = self.db.query(Place).filter(Place.id.in_(place_ids)).all()
        return {row.id: row for row in rows}

    def bulk_upsert_spots(
        self, area_cd: str, signgu_cd: str, spots: list[tuple[str, str]]
    ) -> list[ConcentrationSpot]:
        """(tourist_name, normalized_name) 목록을 일괄 INSERT하고 그 지역 전체를 조회해 돌려준다.

        예전에는 집중률 API 응답 행(한 관광지가 최대 30일치 중복)마다 SELECT 후 없으면
        INSERT까지 반복해서, 페이지 응답이 수천 행이면 DB 조회도 그만큼 반복되는 게 실제
        성능 병목이었다(2026-09-13, STEP4 분석 요청이 안 끝나는 문제로 확인). 이름 기준으로
        이미 dedup된 목록을 받아 (area_cd, signgu_cd, tourist_name) UNIQUE 제약을 이용해
        ON CONFLICT DO NOTHING으로 한 번에 INSERT하고, 그 다음 지역 전체를 한 번 SELECT한다
        — 행마다 하던 조회를 일괄 INSERT/SELECT로 줄인다.

        제약은 이름(constraint=...)이 아니라 컬럼 조합(index_elements=...)으로 지정한다 —
        실제로 테이블을 만드는 0001_unified_schema.py는 supabase/schema.sql의
        `UNIQUE (area_cd, signgu_cd, tourist_name)`(이름 없는 인라인 선언)을 그대로 실행하므로
        Postgres가 자동으로 이름을 붙인다. ConcentrationSpot 모델의
        `UniqueConstraint(..., name="uq_concentration_spot_area_signgu_name")`은 실제 테이블
        생성 경로에서 쓰이지 않아 그 이름이 DB에 존재하지 않는다 — 실제 DB로 검증하다가 발견함
        (`psycopg2.errors.UndefinedObject`). index_elements는 제약 이름과 무관하게 해당 컬럼
        조합을 커버하는 유니크 인덱스/제약을 찾아 매칭하므로 이 불일치의 영향을 받지 않는다.

        commit은 여기서 하지 않는다 — 같은(아직 커밋 안 된) 트랜잭션 안에서도 방금 INSERT한
        행은 바로 이어지는 SELECT에 그대로 보인다. 여기서 commit하면 세션에 쌓인 다른 변경까지
        같이 확정돼버려서, 호출부에서 이후 단계가 실패해도 이미 저장된 관광지를 되돌릴 수 없게
        된다. 실제 commit은 호출부의 기존 커밋 지점에 맡긴다(STEP4는 upsert_mapping/
        upsert_analysis, STEP6은 create_request_with_candidates()의 마지막 commit).
        """
        if spots:
            stmt = pg_insert(ConcentrationSpot).values(
                [
                    {
                        "area_cd": area_cd,
                        "signgu_cd": signgu_cd,
                        "tourist_name": tourist_name,
                        "normalized_name": normalized_name,
                    }
                    for tourist_name, normalized_name in spots
                ]
            ).on_conflict_do_nothing(
                index_elements=["area_cd", "signgu_cd", "tourist_name"]
            )
            self.db.execute(stmt)
        return self.list_spots_by_region(area_cd, signgu_cd)

    def list_spots_by_region(self, area_cd: str, signgu_cd: str) -> list[ConcentrationSpot]:
        return (
            self.db.query(ConcentrationSpot)
            .filter(ConcentrationSpot.area_cd == area_cd, ConcentrationSpot.signgu_cd == signgu_cd)
            .all()
        )

    def get_mapping(self, place_id: UUID) -> PlaceConcentrationMapping | None:
        return (
            self.db.query(PlaceConcentrationMapping)
            .filter(PlaceConcentrationMapping.place_id == place_id)
            .first()
        )

    def get_spot(self, spot_id: int) -> ConcentrationSpot | None:
        return self.db.query(ConcentrationSpot).filter(ConcentrationSpot.id == spot_id).first()

    def upsert_mapping(
        self,
        place_id: UUID,
        concentration_spot_id: int | None,
        match_method: str | None,
        confidence: Decimal | None,
        status: str,
    ) -> PlaceConcentrationMapping | None:
        """자동 매칭 결과를 저장한다. 사람이 이미 approved/rejected로 확정한 매핑은 어떤 경우에도
        (매칭 실패로 지우려는 경우 포함) 덮어쓰거나 삭제하지 않고 그대로 반환한다.
        """
        existing = self.get_mapping(place_id)
        if existing is not None and existing.status in _HUMAN_REVIEWED_STATUSES:
            return existing

        if concentration_spot_id is None:
            if existing is not None:
                self.db.delete(existing)
                self.db.commit()
            return None

        if existing is None:
            existing = PlaceConcentrationMapping(place_id=place_id, match_method=match_method, status=status)
            self.db.add(existing)
        existing.concentration_spot_id = concentration_spot_id
        existing.match_method = match_method
        existing.confidence = confidence
        existing.status = status
        self.db.commit()
        self.db.refresh(existing)
        return existing

    def clear_analysis_for_trip_place(self, trip_place_id: UUID) -> None:
        """장소 교체(STEP7) 시 그 trip_place에 붙어 있던 이전 분석 결과를 지운다.

        place_concentration_mapping은 지우지 않는다 — place_id 기준의 재사용 가능한 사실이라
        다른 trip에서 같은 장소를 참조할 수 있고, 사람이 검수한 값이면 특히 보존해야 한다.
        """
        self.db.query(TripPlaceAnalysis).filter(
            TripPlaceAnalysis.trip_place_id == trip_place_id
        ).delete()

    def write_analysis(
        self,
        trip_place_id: UUID,
        analysis_status: str,
        level: str | None,
        unknown_reason: str | None,
        rule_version: str | None,
    ) -> TripPlaceAnalysis:
        """분석 결과를 세션에만 반영한다. commit은 호출측 트랜잭션에 맡긴다."""
        analysis = (
            self.db.query(TripPlaceAnalysis)
            .filter(TripPlaceAnalysis.trip_place_id == trip_place_id)
            .first()
        )
        if analysis is None:
            analysis = TripPlaceAnalysis(trip_place_id=trip_place_id)
            self.db.add(analysis)
        analysis.analysis_status = analysis_status
        analysis.level = level
        analysis.unknown_reason = unknown_reason
        analysis.rule_version = rule_version
        analysis.analyzed_at = datetime.now(timezone.utc)
        self.db.flush()
        return analysis

    def upsert_analysis(
        self,
        trip_place_id: UUID,
        analysis_status: str,
        level: str | None,
        unknown_reason: str | None,
        rule_version: str | None,
    ) -> TripPlaceAnalysis:
        analysis = self.write_analysis(
            trip_place_id, analysis_status, level, unknown_reason, rule_version
        )
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_analysis_map(self, trip_place_ids: list[UUID]) -> dict[UUID, TripPlaceAnalysis]:
        if not trip_place_ids:
            return {}
        rows = (
            self.db.query(TripPlaceAnalysis)
            .filter(TripPlaceAnalysis.trip_place_id.in_(trip_place_ids))
            .all()
        )
        return {row.trip_place_id: row for row in rows}

    def get_active_replacements_map(self, trip_place_ids: list[UUID]) -> dict[UUID, Replacement]:
        """되돌리지 않은 교체 이력만, trip_place당 가장 최근 1건."""
        if not trip_place_ids:
            return {}
        rows = (
            self.db.query(Replacement)
            .filter(
                Replacement.trip_place_id.in_(trip_place_ids),
                Replacement.reverted_at.is_(None),
            )
            .order_by(desc(Replacement.applied_at))
            .all()
        )
        result: dict[UUID, Replacement] = {}
        for row in rows:
            if row.trip_place_id not in result:
                result[row.trip_place_id] = row
        return result
