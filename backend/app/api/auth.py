"""인증 관련 HTTP 엔드포인트를 정의한다.

회원가입·로그인·토큰 갱신·로그아웃·비밀번호 재설정은 FastAPI 가 Supabase Auth 를 감싼다.
소셜 로그인은 라우트만 제공하고 501 을 반환한다.
"""
from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import get_current_user, http_bearer
from app.db.session import get_db
from app.schemas.auth import (
    AuthSessionResponse,
    LoginRequest,
    MessageResponse,
    PasswordResetRequest,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.schemas.user import CurrentUser
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignupResponse, response_model_exclude_none=True)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    """이메일·비밀번호 회원가입 후 서비스용 profile 생성을 연결한다."""
    return AuthService(db).signup(payload)


@router.post("/login", response_model=AuthSessionResponse, response_model_exclude_none=True)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthSessionResponse:
    """이메일·비밀번호로 로그인하고 액세스/리프레시 토큰을 반환한다."""
    return AuthService(db).login(payload)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """리프레시 토큰으로 액세스 토큰을 재발급한다."""
    return AuthService(db).refresh(payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: CurrentUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> Response:
    """현재 세션을 만료한다. current_user 는 인증 확인용이다."""
    _ = current_user
    token = credentials.credentials if credentials else ""
    AuthService(db).logout(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/password/reset-request", response_model=MessageResponse)
def password_reset_request(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """비밀번호 재설정 메일을 요청한다. 계정 존재 여부는 응답에 드러내지 않는다."""
    return AuthService(db).request_password_reset(payload)


@router.post("/social/{provider}")
def social_login(provider: str, db: Session = Depends(get_db)) -> None:
    """소셜 로그인. 현재는 kakao/google 만 인식하고 501 을 반환한다."""
    AuthService(db).social_login(provider)
