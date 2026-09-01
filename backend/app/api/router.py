"""v1 라우터를 /api 아래로 묶는 조립 파일이다."""
from fastapi import APIRouter

from app.api.v1 import auth, home, schedules, users

api_router = APIRouter()
# 인증, 사용자, 홈, 일정 라우터를 한곳에 등록해 main.py 에서 한 번에 include 하도록 한다.
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(home.router)
api_router.include_router(schedules.router)
