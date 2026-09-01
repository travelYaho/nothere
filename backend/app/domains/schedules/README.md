# schedules 도메인

일정 CRUD와 장소(`schedule_places`)를 담당합니다.

- API: `GET/POST /api/schedules`, `GET/PATCH/DELETE /api/schedules/{id}`
- 서비스: `app/services/schedule_service.py`
- 모델: `Schedule`, `SchedulePlace`
- 소유자 필터: repository의 `user_id` 조건 (FastAPI는 RLS를 우회하므로 필수)
