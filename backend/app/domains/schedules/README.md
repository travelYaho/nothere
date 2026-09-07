# schedules 도메인 (레거시)

`schedules` / `schedule_places` 테이블은 통합 스키마에서 제거되었다.
일정 데이터는 `trip` / `trip_place` 로 이전한다.

현재 `/api/schedules` 는 501을 반환한다. 홈의 draft/recent도 빈 값이다.
