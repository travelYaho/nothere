"""API 라우터를 /api 아래로 묶는 조립 파일이다."""
from fastapi import APIRouter

from app.api import (
    auth,
    experience_tags,
    guide,
    guides,
    home,
    places,
    purpose,
    recommendation,
    regions,
    replacements,
    trips,
    users,
)

api_router = APIRouter()
# 인증, 사용자, 홈, STEP2(지역/선호경험/일정생성), STEP3(장소검색/추가/수정),
# 방문목적, 추천/교체, 가이드북(공유 조회 + 공개 갤러리) 라우터를 한곳에 등록해
# main.py 에서 한 번에 include 한다.
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(home.router)
api_router.include_router(regions.router)
api_router.include_router(experience_tags.router)
api_router.include_router(trips.router)
api_router.include_router(places.router)
api_router.include_router(purpose.router)
api_router.include_router(recommendation.router)
api_router.include_router(replacements.router)
api_router.include_router(guide.router)
api_router.include_router(guides.router)
