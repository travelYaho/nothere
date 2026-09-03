"""지역 목록 조회 API 의 응답 스키마를 정의한다."""
from app.schemas.common import APIModel


class RegionResponse(APIModel):
    """STEP2 지역 선택 드롭다운에 쓰는 최소 정보."""
    id: int
    name: str


class RegionListResponse(APIModel):
    """GET /regions 응답 전체 묶음."""
    regions: list[RegionResponse]
