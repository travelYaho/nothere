"""집중도 분석(STEP4) 관련 조회/저장. 소유권은 항상 부모 Trip.user_id로 확인한다."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.db.models.concentration import ConcentrationSpot, PlaceConcentrationMapping
from app.db.models.place import Place
from app.db.models.recommendation import TripPlaceAnalysis
from app.db.models.region import Region
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

    def get_region(self, region_id: int | None) -> Region | None:
        if region_id is None:
            return None
        return self.db.query(Region).filter(Region.id == region_id).first()

    def get_places_map(self, place_ids: list[UUID]) -> dict[UUID, Place]:
        if not place_ids:
            return {}
        rows = self.db.query(Place).filter(Place.id.in_(place_ids)).all()
        return {row.id: row for row in rows}

    def get_or_create_spot(
        self,
        area_cd: str,
        signgu_cd: str,
        tourist_name: str,
        normalized_name: str,
    ) -> ConcentrationSpot:
        spot = (
            self.db.query(ConcentrationSpot)
            .filter(
                ConcentrationSpot.area_cd == area_cd,
                ConcentrationSpot.signgu_cd == signgu_cd,
                ConcentrationSpot.tourist_name == tourist_name,
            )
            .first()
        )
        if spot is not None:
            return spot
        spot = ConcentrationSpot(
            area_cd=area_cd,
            signgu_cd=signgu_cd,
            tourist_name=tourist_name,
            normalized_name=normalized_name,
        )
        self.db.add(spot)
        self.db.commit()
        self.db.refresh(spot)
        return spot

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

    def upsert_analysis(
        self,
        trip_place_id: UUID,
        analysis_status: str,
        level: str | None,
        unknown_reason: str | None,
        rule_version: str | None,
    ) -> TripPlaceAnalysis:
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
