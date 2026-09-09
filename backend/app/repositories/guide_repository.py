"""가이드북 공개 갤러리/좋아요 관련 SQLAlchemy 접근을 모아 둔 repository 이다."""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.experience_tag import ExperienceTag
from app.db.models.guide_entry import GuideEntry
from app.db.models.guide_like import GuideLike
from app.db.models.profile import Profile
from app.db.models.region import Region
from app.db.models.share_link import ShareLink, ShareLinkVisibility
from app.db.models.preference import TripPreferredExperience
from app.db.models.trip import Trip
from app.db.models.trip_place import TripPlace

PAGE_SIZE = 8
# 카드 부제(by 작성자 · 태그1·태그2)에 노출할 선호경험 태그 최대 개수.
_CARD_TAG_LIMIT = 2


@dataclass
class GuideCard:
    """탐색/좋아요 목록 한 칸을 조립하는 데 필요한 원시 데이터 묶음."""
    trip_id: UUID
    token: str
    title: str
    region_name: str
    place_count: int
    tag_names: list[str]
    author_nickname: str
    cover_image_url: str | None
    like_count: int
    is_liked_by_me: bool


class GuideRepository:
    """share_link/guide_entry/guide_like 조회·조작을 담당한다."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_share_by_token(self, token: str) -> ShareLink | None:
        """존재 여부만 확인한다 — 만료/취소 여부는 호출부에서 별도로 판단한다."""
        return self.db.query(ShareLink).filter(ShareLink.token == token).first()

    @staticmethod
    def is_share_link_gone(link: ShareLink) -> bool:
        """만료되었거나 취소된 링크인지 확인한다."""
        now = datetime.now(timezone.utc)
        return link.revoked_at is not None or (
            link.expires_at is not None and link.expires_at <= now
        )

    def list_public(
        self,
        *,
        viewer_id: UUID,
        sort: str,
        region_id: int | None,
        tag_ids: list[int],
        page: int,
        liked_only: bool,
    ) -> tuple[list[GuideCard], int]:
        """공개(visibility=public) 가이드북 목록을 페이지 단위로 반환한다.

        반환값은 (해당 페이지 카드 목록, 조건에 맞는 전체 개수) 이다.
        """
        query = (
            self.db.query(ShareLink, Trip, Region)
            .join(Trip, Trip.id == ShareLink.trip_id)
            .join(Region, Region.id == Trip.region_id)
            .filter(ShareLink.visibility == ShareLinkVisibility.PUBLIC)
            .filter(ShareLink.revoked_at.is_(None))
        )
        now = datetime.now(timezone.utc)
        query = query.filter(
            (ShareLink.expires_at.is_(None)) | (ShareLink.expires_at > now)
        )

        if region_id is not None:
            query = query.filter(Trip.region_id == region_id)
        if tag_ids:
            query = query.filter(
                exists(
                    select(TripPreferredExperience)
                    .where(TripPreferredExperience.trip_id == Trip.id)
                    .where(TripPreferredExperience.experience_tag_id.in_(tag_ids))
                )
            )
        if liked_only:
            query = query.filter(
                exists(
                    select(GuideLike)
                    .where(GuideLike.share_link_id == ShareLink.id)
                    .where(GuideLike.user_id == viewer_id)
                )
            )

        total_count = query.count()

        if sort == "recent":
            query = query.order_by(ShareLink.created_at.desc())
        else:
            like_count_subq = (
                select(func.count(GuideLike.id))
                .where(GuideLike.share_link_id == ShareLink.id)
                .correlate(ShareLink)
                .scalar_subquery()
            )
            query = query.order_by(like_count_subq.desc(), ShareLink.created_at.desc())

        rows = query.offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE).all()
        cards = [
            self._build_card(share_link, trip, region, viewer_id=viewer_id)
            for share_link, trip, region in rows
        ]
        return cards, total_count

    def _build_card(
        self, share_link: ShareLink, trip: Trip, region: Region, *, viewer_id: UUID
    ) -> GuideCard:
        return GuideCard(
            trip_id=trip.id,
            token=share_link.token,
            title=trip.title,
            region_name=region.name,
            place_count=self._place_count(trip.id),
            tag_names=self._top_tag_names(trip.id),
            author_nickname=self._author_nickname(trip.user_id),
            cover_image_url=self._cover_image_url(trip.id),
            like_count=self.count_likes(share_link.id),
            is_liked_by_me=self.is_liked(share_link.id, viewer_id),
        )

    def _place_count(self, trip_id: UUID) -> int:
        return (
            self.db.query(func.count(TripPlace.id))
            .filter(TripPlace.trip_id == trip_id)
            .scalar()
            or 0
        )

    def _top_tag_names(self, trip_id: UUID) -> list[str]:
        rows = (
            self.db.query(ExperienceTag.name)
            .join(
                TripPreferredExperience,
                TripPreferredExperience.experience_tag_id == ExperienceTag.id,
            )
            .filter(TripPreferredExperience.trip_id == trip_id)
            .order_by(TripPreferredExperience.weight.desc())
            .limit(_CARD_TAG_LIMIT)
            .all()
        )
        return [name for (name,) in rows]

    def _author_nickname(self, user_id: UUID) -> str:
        nickname = (
            self.db.query(Profile.nickname).filter(Profile.id == user_id).scalar()
        )
        return nickname or ""

    def _cover_image_url(self, trip_id: UUID) -> str | None:
        return (
            self.db.query(GuideEntry.image_url)
            .filter(
                GuideEntry.trip_id == trip_id,
                GuideEntry.is_public.is_(True),
                GuideEntry.image_url.isnot(None),
            )
            .order_by(GuideEntry.display_order.asc().nulls_last(), GuideEntry.created_at.asc())
            .limit(1)
            .scalar()
        )

    def count_likes(self, share_link_id: UUID) -> int:
        return (
            self.db.query(func.count(GuideLike.id))
            .filter(GuideLike.share_link_id == share_link_id)
            .scalar()
            or 0
        )

    def is_liked(self, share_link_id: UUID, user_id: UUID) -> bool:
        return (
            self.db.query(GuideLike)
            .filter(GuideLike.share_link_id == share_link_id, GuideLike.user_id == user_id)
            .first()
            is not None
        )

    def add_like(self, share_link_id: UUID, user_id: UUID) -> None:
        """이미 좋아요를 눌렀다면 조용히 무시한다(멱등)."""
        if self.is_liked(share_link_id, user_id):
            return
        self.db.add(GuideLike(share_link_id=share_link_id, user_id=user_id))
        try:
            self.db.commit()
        except IntegrityError:
            # 동시 요청 등으로 UNIQUE 제약에 걸려도 결과적으로 "좋아요 됨" 상태면 성공 취급한다.
            self.db.rollback()

    def remove_like(self, share_link_id: UUID, user_id: UUID) -> None:
        (
            self.db.query(GuideLike)
            .filter(GuideLike.share_link_id == share_link_id, GuideLike.user_id == user_id)
            .delete()
        )
        self.db.commit()

    def list_filter_regions(self) -> list[Region]:
        return (
            self.db.query(Region)
            .filter(Region.is_supported.is_(True))
            .order_by(Region.id)
            .all()
        )

    def list_filter_tags(self) -> list[ExperienceTag]:
        return (
            self.db.query(ExperienceTag)
            .filter(ExperienceTag.is_active.is_(True))
            .order_by(ExperienceTag.display_order, ExperienceTag.id)
            .all()
        )
