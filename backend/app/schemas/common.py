"""모든 API 스키마가 공통으로 상속하는 Pydantic 베이스 모델과 공통 응답 포맷을 정의한다."""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class APIModel(BaseModel):
    """snake_case 필드를 camelCase JSON 으로 노출하도록 기본 설정을 모아 둔다."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ApiResponse(APIModel, Generic[T]):
    """성공 응답 공통 포맷: `{"data": ..., "meta": ...}`."""
    data: T
    meta: dict[str, Any] | None = None


class ApiErrorDetail(APIModel):
    """실패 응답의 error 필드 내부 구조."""
    code: str
    message: str


class ApiError(APIModel):
    """실패 응답 공통 포맷: `{"error": {"code": ..., "message": ...}}`."""
    error: ApiErrorDetail
