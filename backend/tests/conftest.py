"""pytest fixtures 자리이다. 공통 fixture는 여기에 추가한다."""
import os

# 요청 횟수 제한은 같은 IP("testclient")에서 수백 건이 몰리는 테스트를 깨뜨리므로 기본 비활성화한다.
# app 을 import 하기 전에 설정돼야 하며, 제한 동작을 검증하는 테스트만 직접 켠다.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
