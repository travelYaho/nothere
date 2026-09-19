"""기존 place(source_type='tour_api') 중 area_cd/signgu_cd가 비어 있는 행을 보충한다.

alembic 마이그레이션이 아니라 별도 스크립트로 둔다 — 외부 API를 호출하는 작업은
마이그레이션에 넣지 않는다(트랜잭션 재시도/롤백 시 API를 반복 호출하게 되고, 오프라인
SQL 렌더링(--sql)과도 맞지 않는다).

사용법:
    python -m scripts.backfill_place_district_codes [--dry-run]

동작:
- source_type='tour_api'이고 tour_content_id가 있는데 area_cd/signgu_cd가 하나라도 비어
  있는 place만 대상으로 한다.
- 이름으로 TourAPI를 재검색해서 같은 tour_content_id를 가진 결과만 채택한다 — 이름
  유사도로 다른 관광지 정보를 채우지 않는다.
- 판정·적용은 PlaceRepository.preview_district_code_backfill()/apply_district_code_backfill()
  을 그대로 써서 STEP3·STEP6와 같은 규칙을 공유한다.
- --dry-run은 preview_district_code_backfill()(잠금 없는 조회, 절대 쓰지 않음)만 호출한다
  — apply_district_code_backfill()은 실행 모드에서만 부른다.
- 재실행해도 이미 채워진 행은 대상 쿼리에서 자연히 빠지므로 다시 처리하지 않는다(재개 가능).
- API 키·원본 응답 전체는 로그에 남기지 않는다.
"""
import argparse
import logging
import time
from collections import Counter

from app.clients import tour_api
from app.core.logging_setup import suppress_third_party_request_logging
from app.db.models.place import Place
from app.db.session import SessionLocal
from app.repositories.place_repository import PlaceRepository

logger = logging.getLogger("yeogimalgo.backfill_place_district_codes")

_SLEEP_BETWEEN_CALLS_SECONDS = 0.2


def run(dry_run: bool = False) -> None:
    db = SessionLocal()
    repo = PlaceRepository(db)
    try:
        targets = (
            db.query(Place)
            .filter(
                Place.source_type == "tour_api",
                Place.tour_content_id.isnot(None),
                (Place.area_cd.is_(None)) | (Place.signgu_cd.is_(None)),
            )
            .all()
        )
        logger.info("백필 대상 %d건", len(targets))

        status_counts: Counter[str] = Counter()
        unmatched: list[str] = []

        for place in targets:
            try:
                results = tour_api.search_places(place.name)
            except Exception as exc:  # noqa: BLE001 — 외부 API 실패는 이 place만 건너뛰고 계속
                logger.warning("장소 %s 재검색 실패, 건너뜀: %s", place.id, exc)
                status_counts["search_failed"] += 1
                continue

            match = next((r for r in results if r.content_id == place.tour_content_id), None)
            if match is None or not match.area_cd or not match.signgu_cd:
                logger.info("장소 %s(%s) 재검색 결과에서 지역코드를 찾지 못함", place.id, place.name)
                status_counts["no_match"] += 1
                unmatched.append(f"{place.id} ({place.name})")
                time.sleep(_SLEEP_BETWEEN_CALLS_SECONDS)
                continue

            if dry_run:
                status = repo.preview_district_code_backfill(place.id, match.area_cd, match.signgu_cd)
                logger.info(
                    "[dry-run] 장소 %s(%s) 예상 결과: %s (area_cd=%s signgu_cd=%s)",
                    place.id, place.name, status, match.area_cd, match.signgu_cd,
                )
            else:
                status = repo.apply_district_code_backfill(place, match.area_cd, match.signgu_cd)
                db.commit()
                if status == "conflict":
                    logger.warning(
                        "장소 %s 기존 지역코드와 새 응답(%s/%s)이 달라 자동 덮어쓰지 않음 — 수동 확인 필요",
                        place.id, match.area_cd, match.signgu_cd,
                    )

            status_counts[status] += 1
            time.sleep(_SLEEP_BETWEEN_CALLS_SECONDS)

        logger.info(
            "완료: 대상 %d건 — %s",
            len(targets),
            ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items())),
        )
        if unmatched:
            logger.info("재검색으로 못 찾은 장소 목록(%d건): %s", len(unmatched), "; ".join(unmatched))
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # 이 스크립트는 app.main을 거치지 않고 직접 실행되므로, httpx의 요청 URL(쿼리의
    # serviceKey 포함) INFO 로깅을 여기서도 따로 꺼야 한다 — main.py의 설정을
    # 자동으로 물려받지 않는다.
    suppress_third_party_request_logging()
    parser = argparse.ArgumentParser(description="place.area_cd/signgu_cd 백필")
    parser.add_argument("--dry-run", action="store_true", help="실제로 저장하지 않고 무엇을 할지만 출력")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
