"""모델 import 지점을 한곳으로 모아 Alembic 과 앱 초기화에서 재사용한다."""
from app.db.models.profile import Profile
from app.db.models.schedule import Schedule, ScheduleStatus

__all__ = ["Profile", "Schedule", "ScheduleStatus"]
