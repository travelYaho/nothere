"""홈 화면용 요약 데이터를 조립하는 서비스이다.

NOTE: schedules 테이블은 통합 스키마에서 trip 으로 대체됨.
홈의 draft/recent 는 trip 마이그레이션 전까지 빈 값으로 반환한다.
"""
from sqlalchemy.orm import Session

from app.schemas.home import HomeResponse, HomeUserResponse
from app.schemas.user import CurrentUser


class HomeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_home(self, current_user: CurrentUser) -> HomeResponse:
        return HomeResponse(
            user=HomeUserResponse(
                id=current_user.id,
                nickname=current_user.nickname,
                profile_image_url=current_user.profile_image_url,
            ),
            draft_schedule=None,
            recent_schedules=[],
        )
