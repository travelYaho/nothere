"""API 공통 응답 래퍼."""
from typing import Any, Generic, TypeVar

from pydantic import Field

from app.schemas.common import APIModel

T = TypeVar("T")


class Meta(APIModel):
    request_id: str | None = None


class DataResponse(APIModel, Generic[T]):
    data: T
    meta: dict[str, Any] = Field(default_factory=dict)


def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"data": data, "meta": meta or {}}
