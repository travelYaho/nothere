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
        # remainingCount 처럼 code/message 만으로는 표현 안 되는 부가 정보.
        # 키는 이미 camelCase 로 직접 넣는다(이 dict 는 APIModel 을 안 거치므로
        # alias_generator 가 적용되지 않는다).
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
    # 명세서 예시는 소문자 스네이크(invalid_preferred_experience_count)로 적혀 있지만,
    # 기존 코드 컨벤션(AUTH_* 등)에 맞춰 대문자 스네이크로 통일했다.
    INVALID_PREFERRED_EXPERIENCE_COUNT = "INVALID_PREFERRED_EXPERIENCE_COUNT"
    INVALID_TRAVEL_DATE = "INVALID_TRAVEL_DATE"
    DUPLICATE_PLACE_ID = "DUPLICATE_PLACE_ID"
    MINIMUM_PLACES_REQUIRED = "MINIMUM_PLACES_REQUIRED"
    ADDRESS_NOT_FOUND = "ADDRESS_NOT_FOUND"
    GUIDE_NOT_PUBLIC = "GUIDE_NOT_PUBLIC"
    SHARE_LINK_GONE = "SHARE_LINK_GONE"
    NO_PLACES_IN_TRIP = "NO_PLACES_IN_TRIP"
    INVALID_SEARCH_MODE = "INVALID_SEARCH_MODE"
