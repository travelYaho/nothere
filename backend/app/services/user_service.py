"""로그인 사용자 프로필 조회/수정 비즈니스 로직을 담당한다."""
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ErrorCode
from app.repositories.trip_repository import TripRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser, UserResponse, UserStatsResponse, UserUpdateRequest


class UserService:
    """사용자 라우터와 repository 사이에서 예외 처리와 응답 조합을 맡는다."""
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.trips = TripRepository(db)

    def get_me(self, current_user: CurrentUser) -> UserResponse:
        """인증 의존성에서 만든 CurrentUser 를 API 응답 스키마로 옮긴다."""
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            nickname=current_user.nickname,
            profile_image_url=current_user.profile_image_url,
        )

    def update_me(self, current_user: CurrentUser, payload: UserUpdateRequest) -> UserResponse:
        """수정 가능한 필드만 골라 현재 사용자 profile 에 반영한다."""
        profile = self.users.get_by_id(current_user.id)
        if profile is None:
            raise AppError(
                ErrorCode.USER_NOT_FOUND,
                "사용자를 찾을 수 없습니다.",
                status_code=404,
            )

        fields = payload.model_dump(exclude_unset=True)
        try:
            profile = self.users.update(
                profile,
                nickname=fields.get("nickname"),
                profile_image_url=fields.get("profile_image_url"),
                update_image="profile_image_url" in fields,
            )
        except SQLAlchemyError as exc:
            raise AppError(
                ErrorCode.DB_ERROR,
                "사용자 정보를 저장하는 중 오류가 발생했습니다.",
                status_code=500,
            ) from exc

        return UserResponse(
            id=profile.id,
            email=current_user.email,
            nickname=profile.nickname,
            profile_image_url=profile.profile_image_url,
        )

    def get_stats(self, current_user: CurrentUser) -> UserStatsResponse:
        """마이페이지 통계 카드: 일정 생성 시작 수 / 확정까지 간 수."""
        total, confirmed = self.trips.count_stats(current_user.id)
        return UserStatsResponse(total_trip_count=total, confirmed_trip_count=confirmed)
