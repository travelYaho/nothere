"""방문 목적 태그 조회/저장 API 의 요청/응답 스키마를 정의한다."""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class PurposeTagResponse(APIModel):
    """선택된 방문 목적 태그 한 건."""
    id: int
    name: str


class PurposeGetResponse(APIModel):
    """GET /trip-places/{tripPlaceId}/purpose 응답."""
    trip_place_id: UUID
    purpose_tags: list[PurposeTagResponse]


class PurposePutRequest(APIModel):
    """PUT /trip-places/{tripPlaceId}/purpose 요청. 0개 이상(빈 배열=전체 해제 가능)."""
    purpose_tag_ids: list[int] = Field(default_factory=list)


class PurposePutResponse(APIModel):
    """PUT /trip-places/{tripPlaceId}/purpose 200 응답."""
    trip_place_id: UUID
    purpose_tags: list[PurposeTagResponse]
    updated_at: datetime
