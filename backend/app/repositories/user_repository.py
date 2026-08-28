"""profiles 테이블에 대한 SQLAlchemy 접근을 모아 둔 repository 이다."""
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.profile import Profile


class UserRepository:
    """서비스 계층이 직접 ORM 세부 구현을 알지 않도록 profile 쿼리를 감싼다."""
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: UUID) -> Profile | None:
        """profile PK 로 단건 조회한다."""
        return self.db.get(Profile, user_id)

    def create(self, user_id: UUID, nickname: str) -> Profile:
        """회원가입 직후 auth.users.id 와 같은 UUID 로 profile 을 생성한다."""
        profile = Profile(id=user_id, nickname=nickname)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update(
        self,
        profile: Profile,
        nickname: str | None = None,
        profile_image_url: str | None = None,
        update_image: bool = False,
    ) -> Profile:
        """부분 수정 요청에 맞춰 nickname / profile_image_url 을 갱신한다."""
        if nickname is not None:
            profile.nickname = nickname
        if update_image:
            profile.profile_image_url = profile_image_url
        self.db.commit()
        self.db.refresh(profile)
        return profile
