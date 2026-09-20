"""STEP2 조건입력·수정·삭제(여행 생성/수정/삭제) + Trip 액션(경로/확정/가이드/공유)
엔드포인트를 정의한다.
"""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.domains.analysis.service import AnalysisService
from app.domains.recommendation.service import RecommendationService
from app.schemas.common import ApiResponse
from app.schemas.envelope import ok
from app.schemas.recommendation import GuideMemoRequest, ShareLinkRequest
from app.schemas.trip import (
    TripConditionsUpdateRequest,
    TripConditionsUpdateResponse,
    TripCreateRequest,
    TripCreateResponse,
    TripDetailResponse,
    TripListResponse,
)
from app.schemas.user import CurrentUser
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("", response_model=ApiResponse[TripCreateResponse], status_code=201)
def create_trip(
    payload: TripCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[TripCreateResponse]:
    """STEP2 폼 제출 시 여행 일정을 생성하고 STEP3 진입 정보를 반환한다."""
    return ApiResponse(data=TripService(db).create_trip(current_user, payload))


@router.get("", response_model=ApiResponse[TripListResponse])
def list_trips(
    status_filter: Literal["draft", "confirmed"] | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[TripListResponse]:
    """내 일정 목록 — 보관함 "일정" 탭이 쓴다. status 미지정 시 전체."""
    return ApiResponse(
        data=TripService(db).list_trips(current_user, status_filter=status_filter, page=page)
    )


@router.get("/{trip_id}", response_model=ApiResponse[TripDetailResponse])
def get_trip(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[TripDetailResponse]:
    """일정 상세(이어서 진행) — 조건 + 등록된 장소 목록을 함께 반환한다."""
    return ApiResponse(data=TripService(db).get_trip_detail(current_user, trip_id))


@router.patch("/{trip_id}/conditions", response_model=ApiResponse[TripConditionsUpdateResponse])
def update_trip_conditions(
    trip_id: UUID,
    payload: TripConditionsUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiResponse[TripConditionsUpdateResponse]:
    """여행 날짜/지역/이동수단/허용시간/선호경험을 부분 수정한다."""
    return ApiResponse(data=TripService(db).update_conditions(current_user, trip_id, payload))


@router.delete("/{trip_id}", status_code=204)
def delete_trip(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """여행 일정을 하드 삭제한다(TripPlace 등은 FK cascade로 함께 삭제)."""
    TripService(db).delete_trip(current_user, trip_id)


@router.post("/{trip_id}/analysis")
def run_analysis(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """STEP4 — 일정 내 모든 장소의 집중도를 분석해 저장하고 결과를 반환한다."""
    data = AnalysisService(db).run_analysis(current_user, trip_id)
    return ok(data)


@router.get("/{trip_id}/analysis")
def get_analysis(
    trip_id: UUID,
    status: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """저장된 분석 결과를 조회한다. status=CROWDED 면 아직 미해결인 혼잡 장소만 반환한다."""
    data = AnalysisService(db).get_analysis(current_user, trip_id, status)
    return ok(data)


@router.get("/{trip_id}/remaining-congested")
def remaining_congested(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).remaining_congested(trip_id, current_user)
    return ok(data)


@router.post("/{trip_id}/confirm")
def confirm_trip(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).confirm(trip_id, current_user)
    return ok(data)


@router.get("/{trip_id}/guide")
def trip_guide(
    trip_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).get_guide(trip_id, current_user)
    return ok(data)


@router.patch("/{trip_id}/guide/memo")
def update_guide_memo(
    trip_id: UUID,
    payload: GuideMemoRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = RecommendationService(db).update_guide_memo(
        trip_id, current_user, payload.content
    )
    return ok(data)


@router.post("/{trip_id}/share-link", status_code=status.HTTP_201_CREATED)
def share_link(
    trip_id: UUID,
    payload: ShareLinkRequest | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = payload or ShareLinkRequest()
    data = RecommendationService(db).create_share_link(
        trip_id, current_user, body.visibility
    )
    return ok(data)
