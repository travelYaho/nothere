"""가이드북 공개 갤러리/좋아요 관련 SQLAlchemy 접근을 모아 둔 repository 이다."""
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clients.photo_gallery import image_for_place
from app.db.models.experience_tag import ExperienceTag
from app.db.models.guide_like import GuideLike
from app.db.models.place import Place
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
    """탐색/좋아요/내 목록 한 칸을 조립하는 데 필요한 원시 데이터 묶음.

    token 은 공유 링크가 있을 때만 채워진다 — 공개 갤러리/좋아요 카드는 항상
    있지만, "내가 만든" 카드는 한 번도 공유하지 않은 트립일 수 있어 없을 수 있다.
    """
    trip_id: UUID
    token: str | None
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

    def get_top_public(self) -> tuple[ShareLink, Trip, Region, int] | None:
        """공개 가이드북 중 좋아요가 가장 많은 1건과 좋아요 수를 반환한다(동률이면 최신순).

        홈 상단 추천 카드용이라 목록 조회(list_public)의 카드 조립 없이 필요한 값만 뽑는다.
        """
        now = datetime.now(timezone.utc)
        like_count_subq = (
            select(func.count(GuideLike.id))
            .where(GuideLike.share_link_id == ShareLink.id)
            .correlate(ShareLink)
            .scalar_subquery()
        )
        row = (
            self.db.query(ShareLink, Trip, Region, like_count_subq)
            .join(Trip, Trip.id == ShareLink.trip_id)
            .join(Region, Region.id == Trip.region_id)
            .filter(ShareLink.visibility == ShareLinkVisibility.PUBLIC)
            .filter(ShareLink.revoked_at.is_(None))
            .filter((ShareLink.expires_at.is_(None)) | (ShareLink.expires_at > now))
            .order_by(like_count_subq.desc(), ShareLink.created_at.desc())
            .first()
        )
        if row is None:
            return None
        share_link, trip, region, like_count = row
        return share_link, trip, region, int(like_count or 0)

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
        cards = self._build_cards(rows, viewer_id=viewer_id)
        return cards, total_count

    def list_owned(self, *, owner_id: UUID, page: int) -> tuple[list[GuideCard], int]:
        """내가 만든(확정한) 가이드북 목록을 최근 순으로 페이지 단위로 반환한다.

        list_public 과 달리 ShareLink 존재 여부가 기준이 아니다 — 가이드북 화면
        (GET /trips/{id}/guide) 은 공유 링크를 안 만들어도 확정된 트립이면 바로
        조회되므로, 목록도 "내 확정 트립"을 기준으로 삼는다(공유는 선택 사항).
        좋아요 수/여부 표시를 위해 ShareLink 는 LEFT JOIN 으로 붙이되(없으면
        0/false), 같은 트립을 여러 번 공유했을 수 있어 트립당 가장 최근 활성
        링크 하나만 붙인다.
        """
        now = datetime.now(timezone.utc)
        active = ShareLink.revoked_at.is_(None) & (
            (ShareLink.expires_at.is_(None)) | (ShareLink.expires_at > now)
        )
        latest_share_link_id = (
            select(ShareLink.id)
            .where(ShareLink.trip_id == Trip.id)
            .where(active)
            .order_by(ShareLink.created_at.desc(), ShareLink.id.desc())
            .limit(1)
            .correlate(Trip)
            .scalar_subquery()
        )

        query = (
            self.db.query(Trip, Region, ShareLink)
            .join(Region, Region.id == Trip.region_id)
            .outerjoin(ShareLink, ShareLink.id == latest_share_link_id)
            .filter(Trip.user_id == owner_id)
            .filter(Trip.status == "confirmed")
        )

        total_count = query.count()
        rows = (
            query.order_by(Trip.updated_at.desc(), Trip.id.desc())
            .offset((page - 1) * PAGE_SIZE)
            .limit(PAGE_SIZE)
            .all()
        )
        cards = self._build_cards(
            [(share_link, trip, region) for trip, region, share_link in rows],
            viewer_id=owner_id,
        )
        return cards, total_count

    def _build_cards(
        self,
        rows: list[tuple[ShareLink | None, Trip, Region]],
        *,
        viewer_id: UUID,
    ) -> list[GuideCard]:
        """카드 목록을 조립한다. 카드마다 장소 수/태그/작성자/커버/좋아요를 따로 조회하면
        페이지당 (카드 수 × 6) 번 DB 왕복이 나서(원격 DB라 수 초), 항목별로 IN 절 한 번씩
        모아 조회한 뒤 메모리에서 붙인다 — 카드 수와 무관하게 쿼리 수가 고정된다.
        """
        if not rows:
            return []
        trip_ids = [trip.id for _, trip, _ in rows]
        user_ids = list({trip.user_id for _, trip, _ in rows})
        link_ids = [link.id for link, _, _ in rows if link is not None]

        place_counts = self._place_counts(trip_ids)
        tag_names = self._top_tag_names_map(trip_ids)
        nicknames = self._author_nicknames(user_ids)
        covers = self._cover_image_urls(trip_ids)
        like_counts = self._like_counts(link_ids)
        liked = self._liked_link_ids(link_ids, viewer_id)

        return [
            GuideCard(
                trip_id=trip.id,
                token=link.token if link else None,
                title=trip.title,
                region_name=region.name,
                place_count=place_counts.get(trip.id, 0),
                tag_names=tag_names.get(trip.id, []),
                author_nickname=nicknames.get(trip.user_id) or "",
                cover_image_url=covers.get(trip.id),
                like_count=like_counts.get(link.id, 0) if link else 0,
                is_liked_by_me=link.id in liked if link else False,
            )
            for link, trip, region in rows
        ]

    def _place_counts(self, trip_ids: list[UUID]) -> dict[UUID, int]:
        rows = (
            self.db.query(TripPlace.trip_id, func.count(TripPlace.id))
            .filter(TripPlace.trip_id.in_(trip_ids))
            .group_by(TripPlace.trip_id)
            .all()
        )
        return dict(rows)

    def _top_tag_names_map(self, trip_ids: list[UUID]) -> dict[UUID, list[str]]:
        rows = (
            self.db.query(TripPreferredExperience.trip_id, ExperienceTag.name)
            .join(ExperienceTag, TripPreferredExperience.experience_tag_id == ExperienceTag.id)
            .filter(TripPreferredExperience.trip_id.in_(trip_ids))
            .order_by(TripPreferredExperience.trip_id, TripPreferredExperience.weight.desc())
            .all()
        )
        result: dict[UUID, list[str]] = {}
        for trip_id, name in rows:
            names = result.setdefault(trip_id, [])
            if len(names) < _CARD_TAG_LIMIT:
                names.append(name)
        return result

    def cover_image_url(self, trip_id: UUID) -> str | None:
        """공개 가이드 카드·홈 추천 배너에 쓰는 대표 이미지. DB에 저장하지 않고 관광 API에서 바로 가져온다."""
        return self._cover_image_urls([trip_id]).get(trip_id)

    def _author_nicknames(self, user_ids: list[UUID]) -> dict[UUID, str]:
        rows = self.db.query(Profile.id, Profile.nickname).filter(Profile.id.in_(user_ids)).all()
        return dict(rows)

    def _cover_image_urls(self, trip_ids: list[UUID]) -> dict[UUID, str]:
        """트립별 첫 장소 사진을 관광 API에서 바로 가져온다. URL은 DB에 저장하지 않는다."""
        if not trip_ids:
            return {}
        rows = (
            self.db.query(TripPlace.trip_id, Place.tour_content_id, Place.name)
            .join(Place, Place.id == TripPlace.place_id)
            .filter(TripPlace.trip_id.in_(trip_ids))
            .order_by(TripPlace.trip_id, TripPlace.position.asc())
            .all()
        )
        first: dict[UUID, tuple[str | None, str | None]] = {}
        for trip_id, content_id, name in rows:
            first.setdefault(trip_id, (content_id, name))
        if not first:
            return {}

        items = list(first.items())
        executor = ThreadPoolExecutor(max_workers=min(len(items), 8))
        try:
            futures = {
                trip_id: executor.submit(
                    image_for_place,
                    SimpleNamespace(tour_content_id=content_id, name=name),
                )
                for trip_id, (content_id, name) in items
            }
            wait(list(futures.values()), timeout=4.0)
            result: dict[UUID, str] = {}
            for trip_id, fut in futures.items():
                if not (fut.done() and fut.exception() is None):
                    continue
                url = fut.result()
                if isinstance(url, str) and url:
                    result[trip_id] = url
            return result
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _like_counts(self, share_link_ids: list[UUID]) -> dict[UUID, int]:
        if not share_link_ids:
            return {}
        rows = (
            self.db.query(GuideLike.share_link_id, func.count(GuideLike.id))
            .filter(GuideLike.share_link_id.in_(share_link_ids))
            .group_by(GuideLike.share_link_id)
            .all()
        )
        return dict(rows)

    def _liked_link_ids(self, share_link_ids: list[UUID], user_id: UUID) -> set[UUID]:
        if not share_link_ids:
            return set()
        rows = (
            self.db.query(GuideLike.share_link_id)
            .filter(GuideLike.share_link_id.in_(share_link_ids), GuideLike.user_id == user_id)
            .all()
        )
        return {share_link_id for (share_link_id,) in rows}

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
