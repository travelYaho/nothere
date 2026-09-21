"""IP 기준 요청 횟수 제한(rate limit)을 정의한다.

전역 기본 한도는 SlowAPIMiddleware 가 모든 라우트에 적용하고, 남용 위험이 큰
엔드포인트(장소 검색)는 데코레이터로 더 낮은 한도를 추가한다.
저장소가 프로세스 메모리라 워커/인스턴스가 여러 개면 한도가 각각 따로 센다.

프록시 뒤에서 배포하면 request.client.host 가 프록시 IP 가 되어 모든 사용자가 한
버킷을 공유한다. uvicorn 에 `--proxy-headers --forwarded-allow-ips=<프록시 IP>` 를
줘서 X-Forwarded-For 가 반영되게 해야 한다(backend/README.md 참고).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

DEFAULT_LIMIT = "120/minute"
SEARCH_LIMIT = "30/minute"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[DEFAULT_LIMIT],
    enabled=settings.RATE_LIMIT_ENABLED,
)
