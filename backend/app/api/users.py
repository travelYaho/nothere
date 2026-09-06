"""로그인 사용자 정보 조회/수정 엔드포인트를 정의한다.

인증은 get_current_user 에 맡기고, 실제 비즈니스 로직은 UserService 가 처리한다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.user import CurrentUser, UserResponse, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """현재 로그인 사용자의 기본 프로필 정보를 반환한다."""
    return UserService(db).get_me(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """닉네임과 프로필 이미지 URL 을 부분 수정한다."""
    return UserService(db).update_me(current_user, payload)
