"""모델 import 지점을 한곳으로 모아 Alembic 과 앱 초기화에서 재사용한다."""
from app.db.models.api_fetch_log import ApiFetchLog
from app.db.models.concentration import ConcentrationSpot, PlaceConcentrationMapping
from app.db.models.experience_tag import ExperienceTag
from app.db.models.guide_entry import GuideEntry
from app.db.models.place import Place
from app.db.models.preference import (
    PlaceExperienceTag,
    TripPlacePurpose,
    TripPreferredExperience,
    UserLongTermPreference,
)
from app.db.models.profile import Profile
from app.db.models.recommendation import (
    RecommendationCandidate,
    RecommendationInteraction,
    RecommendationRanking,
    RecommendationReason,
    RecommendationRequest,
    RecommendationRoute,
    TripPlaceAnalysis,
)
from app.db.models.region import Region
from app.db.models.replacement import Replacement
from app.db.models.route_cache import RouteCache
from app.db.models.share_link import ShareLink
from app.db.models.trip import Trip
from app.db.models.trip_place import TripPlace

__all__ = [
    "Profile",
    "ApiFetchLog",
    "Region",
    "ExperienceTag",
    "Place",
    "Trip",
    "TripPlace",
    "TripPlacePurpose",
    "TripPreferredExperience",
    "PlaceExperienceTag",
    "UserLongTermPreference",
    "ConcentrationSpot",
    "PlaceConcentrationMapping",
    "TripPlaceAnalysis",
    "RecommendationRequest",
    "RecommendationCandidate",
    "RecommendationRanking",
    "RecommendationRoute",
    "RecommendationReason",
    "RecommendationInteraction",
    "RouteCache",
    "Replacement",
    "ShareLink",
    "GuideEntry",
]
