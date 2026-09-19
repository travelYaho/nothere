"""외부 API 클라이언트의 예외 메시지에서 인증키를 마스킹하는 공용 유틸.

TourAPI·집중률 API는 serviceKey를 쿼리 파라미터로 받는다. httpx 예외(특히
HTTPStatusError)의 str()에는 요청 URL 전체가 쿼리 포함으로 그대로 들어있어서,
그 메시지를 그대로 로그/새 예외 메시지로 옮기면 인증키가 평문으로 샌다.
"""
import re

_SERVICE_KEY_PATTERN = re.compile(r"(serviceKey=)[^&\s'\"]*", re.IGNORECASE)


def redact_service_key(text: str) -> str:
    """문자열에 담긴 serviceKey=<값> 쿼리 파라미터를 serviceKey=***로 치환한다."""
    return _SERVICE_KEY_PATTERN.sub(r"\1***", text)
