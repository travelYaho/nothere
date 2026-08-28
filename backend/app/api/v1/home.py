"""로그인 사용자의 홈 화면 요약 엔드포인트를 정의한다.

이 파일은 전체 일정 기능이 아니라 홈에 필요한 최소 요약 응답만 다룬다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.home import HomeResponse
from app.schemas.user import CurrentUser
from app.services.home_service import HomeService

router = APIRouter(tags=["home"])


# [1주차 범위] 홈 API는 전체 일정 API를 대체하지 않는다.
# draftSchedule/recentSchedules 요약만 반환하며, GET/DELETE /api/schedules* 는 미구현.
@router.get("/home", response_model=HomeResponse)
def get_home(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HomeResponse:
    """현재 사용자 기준으로 홈 요약 데이터를 한 번에 반환한다."""
    return HomeService(db).get_home(current_user)
