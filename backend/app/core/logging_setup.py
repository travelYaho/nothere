"""외부 라이브러리 로거의 민감정보 노출을 막는 공통 설정.

httpx/httpcore는 기본으로 요청 URL 전체(쿼리 파라미터 포함)를 INFO 레벨로 로깅한다.
TourAPI·집중률 API는 serviceKey를 쿼리 파라미터로 받으므로, 이 두 라이브러리가 그 값을
직접 로깅하지 않도록 매 진입점(FastAPI 앱, 독립 실행 스크립트)에서 호출해야 한다.
main.py를 임포트하지 않는 스크립트(예: scripts/backfill_place_district_codes.py)는 이
설정을 자동으로 물려받지 않으므로, 그런 스크립트도 반드시 이 함수를 직접 불러야 한다.
"""
import logging


def suppress_third_party_request_logging() -> None:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
