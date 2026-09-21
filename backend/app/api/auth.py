"""인증 관련 HTTP 엔드포인트를 정의한다.

소셜(카카오) 로그인만 지원한다. OAuth 직후 profile 보정만 FastAPI 가 처리하고,
로그인/로그아웃/토큰 갱신은 프론트엔드가 Supabase Auth 를 직접 사용한다.
카카오 연결 해제 웹훅은 카카오가 서버로 직접 POST/GET 한다.
"""
import json
import logging
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.core.security import AuthUser, get_auth_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.kakao_webhook_service import KakaoWebhookService, kakao_admin_authorized

logger = logging.getLogger("yeogimalgo")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/ensure-profile", response_model=ApiResponse[UserResponse])
def ensure_profile(
    auth_user: AuthUser = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> ApiResponse[UserResponse]:
    """카카오 등 OAuth 첫 로그인 때 서비스 profile 이 없으면 생성한다."""
    return ApiResponse(data=AuthService(db).ensure_profile(auth_user))


async def _kakao_unlink_payload(request: Request) -> dict[str, str]:
    data = {key: str(value) for key, value in request.query_params.items()}
    if request.method != "POST":
        return data
    try:
        raw = await request.body()
    except Exception:
        return data
    if not raw:
        return data
    content_type = request.headers.get("content-type", "")
    try:
        if "application/json" in content_type:
            body = json.loads(raw.decode())
            if isinstance(body, dict):
                data.update(
                    {str(key): str(value) for key, value in body.items() if value is not None}
                )
            return data
        for key, value in parse_qsl(raw.decode(), keep_blank_values=True):
            data[key] = value
    except Exception:
        logger.exception("kakao unlink payload parse failed")
    return data


@router.api_route("/kakao/unlink", methods=["GET", "POST"])
async def kakao_unlink(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """카카오 연결 해제 웹훅. 인증 실패가 아니면 3초 내 200 을 반환한다."""
    if not kakao_admin_authorized(request.headers.get("Authorization")):
        raise AppError(
            ErrorCode.UNAUTHORIZED,
            "카카오 웹훅 인증에 실패했습니다.",
            status_code=401,
        )

    payload = await _kakao_unlink_payload(request)
    kakao_user_id = payload.get("user_id", "").strip()
    if kakao_user_id:
        try:
            KakaoWebhookService(db).unlink(kakao_user_id)
        except Exception:
            logger.exception("kakao unlink webhook failed")

    return Response(status_code=200)
