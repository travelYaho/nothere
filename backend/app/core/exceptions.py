"""서비스 전역에서 공통으로 쓰는 예외와 에러 코드를 정의한다."""
from typing import Any


class AppError(Exception):
    """HTTP 응답으로 직결되는 업무 예외를 담는 커스텀 예외."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """스펙 형식 {error: {code, message, ...}} 으로 직렬화한다."""
        payload = {"code": self.code, "message": self.message, **self.extra}
        return {"error": payload}

    def to_legacy_dict(self) -> dict[str, Any]:
        """기존 프론트 호환용 {code, message}."""
        return {"code": self.code, "message": self.message}


class ErrorCode:
    """반복 문자열을 상수로 모아 라우터/서비스 전반에서 재사용한다."""

    AUTH_EMAIL_ALREADY_EXISTS = "AUTH_EMAIL_ALREADY_EXISTS"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    SCHEDULE_NOT_FOUND = "SCHEDULE_NOT_FOUND"
    DB_ERROR = "DB_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    CONFLICT = "CONFLICT"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    EXTERNAL_API_UNAVAILABLE = "EXTERNAL_API_UNAVAILABLE"
    UNRESOLVED_CONGESTED_PLACES = "unresolved_congested_places"
    SHARE_LINK_GONE = "SHARE_LINK_GONE"
    NO_PLACES_IN_TRIP = "NO_PLACES_IN_TRIP"
    INVALID_SEARCH_MODE = "INVALID_SEARCH_MODE"
