"""모델 import 지점을 한곳으로 모아 Alembic 과 앱 초기화에서 재사용한다."""
from app.db.models.auth import auth_users  # noqa: F401  (Profile.id FK 대상 스텁)
from app.db.models.experience_tag import ExperienceTag
from app.db.models.guide_entry import GuideEntry
from app.db.models.guide_like import GuideLike
from app.db.models.place import Place, PlaceExperienceTag
from app.db.models.profile import Profile
from app.db.models.region import Region
from app.db.models.share_link import ShareLink, ShareLinkVisibility
from app.db.models.trip import (
    IN_PROGRESS_STATUSES,
    Trip,
    TripPlace,
    TripPlacePurpose,
    TripPreferredExperience,
    TripStatus,
)
from app.db.models.user_preference import UserLongTermPreference

__all__ = [
    "ExperienceTag",
    "GuideEntry",
    "GuideLike",
    "IN_PROGRESS_STATUSES",
    "Place",
    "PlaceExperienceTag",
    "Profile",
    "Region",
    "ShareLink",
    "ShareLinkVisibility",
    "Trip",
    "TripPlace",
    "TripPlacePurpose",
    "TripPreferredExperience",
    "TripStatus",
    "UserLongTermPreference",
]
