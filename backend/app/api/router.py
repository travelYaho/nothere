"""API 라우터를 /api 아래로 묶는 조립 파일이다."""
from fastapi import APIRouter

from app.api import (
    auth,
    experience_tags,
    guide,
    home,
    recommendation,
    replacements,
    schedules,
    trips,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(home.router)
api_router.include_router(schedules.router)
api_router.include_router(recommendation.router)
api_router.include_router(replacements.router)
api_router.include_router(trips.router)
api_router.include_router(guide.router)
api_router.include_router(experience_tags.router)
