"""추천·교체·공유 API Pydantic 스키마."""
from uuid import UUID

from app.schemas.common import APIModel


class RouteScoreRequest(APIModel):
    trip_place_id: UUID | None = None
    transport_mode: str | None = None
    extra_time_limit_minutes: int | None = None


class ReplacementPreviewRequest(APIModel):
    candidate_id: UUID


class ReplacementCreateRequest(APIModel):
    trip_place_id: UUID
    candidate_id: UUID


class ShareLinkRequest(APIModel):
    visibility: str = "link"


class RecommendationRequestCreate(APIModel):
    """STEP5(방문 목적 선택) 결과를 담아 STEP6 후보 탐색을 요청한다."""
    purpose_tag_ids: list[int] | None = None
    search_mode: str | None = None
