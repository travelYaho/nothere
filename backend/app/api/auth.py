"""인증 관련 HTTP 엔드포인트를 정의한다.

회원가입(signup)과 OAuth 직후 profile 보정만 FastAPI 가 처리한다.
로그인/로그아웃/토큰 갱신은 프론트엔드가 Supabase Auth 를 직접 사용한다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import AuthUser, get_auth_user
from app.db.session import get_db
from app.schemas.auth import SignupRequest, SignupResponse
from app.schemas.common import ApiResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=ApiResponse[SignupResponse],
    response_model_exclude_none=True,
)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> ApiResponse[SignupResponse]:
    """이메일·비밀번호 회원가입 후 서비스용 profile 생성을 연결한다."""
    return ApiResponse(data=AuthService(db).signup(payload))


@router.post("/ensure-profile", response_model=ApiResponse[UserResponse])
def ensure_profile(
    auth_user: AuthUser = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> ApiResponse[UserResponse]:
    """카카오 등 OAuth 첫 로그인 때 서비스 profile 이 없으면 생성한다."""
    return ApiResponse(data=AuthService(db).ensure_profile(auth_user))
