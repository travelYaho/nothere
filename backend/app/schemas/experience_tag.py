"""선호 경험 태그 목록 조회 API 의 응답 스키마를 정의한다."""
from app.schemas.common import APIModel


class ExperienceTagResponse(APIModel):
    """STEP2 선호경험/방문목적 다중선택 UI에 쓰는 최소 정보."""
    id: int
    name: str


class ExperienceTagListResponse(APIModel):
    """GET /experience-tags 응답 전체 묶음."""
    experience_tags: list[ExperienceTagResponse]
