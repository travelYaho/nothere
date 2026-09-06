# recommendation 도메인

혼잡 장소 대안 후보의 경로(거리·이동시간) 점수를 계산하고, 교체·확정·가이드·공유를 담당합니다.

- `scoring.py` — routeScore / eligibility / reason
- `route.py` — Kakao Directions + haversine + `route_cache`
- `service.py` — route-scores / candidates / preview / replace / confirm / guide / share

최종 totalScore·순위(rank)는 이 도메인에서 확정하지 않습니다.
