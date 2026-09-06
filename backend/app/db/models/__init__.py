"""모델 import 지점을 한곳으로 모아 Alembic 과 앱 초기화에서 재사용한다."""
from app.db.models.guide_entry import GuideEntry
from app.db.models.place import Place
from app.db.models.profile import Profile
from app.db.models.recommendation import (
    RecommendationCandidate,
    RecommendationInteraction,
    RecommendationRanking,
    RecommendationRequest,
    TripPlaceAnalysis,
)
from app.db.models.replacement import Replacement
from app.db.models.route_cache import RouteCache
from app.db.models.schedule import Schedule, ScheduleStatus
from app.db.models.schedule_place import SchedulePlace
from app.db.models.share_link import ShareLink
from app.db.models.trip import Trip
from app.db.models.trip_place import TripPlace

__all__ = [
    "Profile",
    "Schedule",
    "SchedulePlace",
    "ScheduleStatus",
    "Place",
    "Trip",
    "TripPlace",
    "TripPlaceAnalysis",
    "RecommendationRequest",
    "RecommendationCandidate",
    "RecommendationRanking",
    "RecommendationInteraction",
    "RouteCache",
    "Replacement",
    "ShareLink",
    "GuideEntry",
]
