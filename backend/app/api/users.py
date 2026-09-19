"""로그인 사용자 정보 조회/수정 엔드포인트를 정의한다.

인증은 get_current_user 에 맡기고, 실제 비즈니스 로직은 UserService 가 처리한다.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.user import CurrentUser, UserResponse, UserStatsResponse, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[UserResponse]:
    """현재 로그인 사용자의 기본 프로필 정보를 반환한다."""
    return ApiResponse(data=UserService(db).get_me(current_user))


@router.get("/me/stats", response_model=ApiResponse[UserStatsResponse])
def get_me_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[UserStatsResponse]:
    """마이페이지 통계 카드(점검한 일정/확정 일정)를 반환한다."""
    return ApiResponse(data=UserService(db).get_stats(current_user))


@router.patch("/me", response_model=ApiResponse[UserResponse])
def update_me(
    payload: UserUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[UserResponse]:
    """닉네임과 프로필 이미지 URL 을 부분 수정한다."""
    return ApiResponse(data=UserService(db).update_me(current_user, payload))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """회원 탈퇴: 계정과 소유 데이터(일정·가이드북·좋아요)를 모두 삭제한다."""
    UserService(db).delete_me(current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
