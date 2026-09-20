/**
 * TripPlacesForm — STEP3 "내 여행 일정 만들기" (장소 등록) 화면.
 * Figma: 여기말GO / node 48:2979 "일정 등록" (리스트) + 48:3158 "검색 바텀 시트"
 * (검색바에 포커스를 주면 바텀시트가 뜨는, 같은 화면의 두 가지 상태다)
 *
 * "이동 X분"/"예상 이동 OO분" 처럼 장소 간 이동시간을 보여주는 부분은 구현하지
 * 않았다 — 그건 경로 계산(Part3 담당, STEP4~6)이 필요한 값이라 지금은 낼 수
 * 있는 실제 데이터가 없다. 지도 영역도 Figma 원본 주석 그대로 "준비 중" placeholder다.
 */
import { useCallback, useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Close, Grip, Pencil, Search } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { StepHeader } from "@/features/trips/components/StepHeader"
import { SearchBottomSheet } from "@/features/trips/components/SearchBottomSheet"
import { getTripDetail } from "@/features/trips/api/tripsApi"
import {
  addPlaceToTrip,
  removeTripPlace,
  reorderTripPlaces,
  searchPlaces,
  updateTripPlaceVisit,
} from "@/features/trips/api/placesApi"
import { COMPANION_LABELS } from "@/features/trips/constants"
import { useLongPressReorder } from "@/features/trips/hooks/useLongPressReorder"
import {
  applyReorder,
  sortPlacesForDisplay,
  withVisitOrder,
} from "@/features/trips/utils/placeOrder"
import type { CompanionType, PlaceSearchItem, TripDetailResponse, TripPlaceDetail } from "@/features/trips/types"
import { ApiError } from "@/types/api"

const SEARCH_DEBOUNCE_MS = 350
// 백엔드 검색어 상한(50자)과 맞춘다. 한글 조합 중에는 input maxLength 가 1자 넘게 통과해
// 422 가 나므로, 요청 직전에도 잘라서 보낸다(입력 state 를 자르면 조합이 끊긴다).
const SEARCH_KEYWORD_MAX_LENGTH = 50
const WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"]

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) {
    if (/failed to fetch|network/i.test(err.message)) {
      return "서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."
    }
    return err.message
  }
  return "요청 중 문제가 발생했습니다."
}

function formatConditionSummary(trip: TripDetailResponse): string {
  const parts: string[] = []
  if (trip.travelDate) {
    const d = new Date(`${trip.travelDate}T00:00:00`)
    parts.push(
      `${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")} (${WEEKDAY_LABELS[d.getDay()]})`,
    )
  }
  parts.push(trip.regionName)
  if (trip.companionType) {
    parts.push(COMPANION_LABELS[trip.companionType as CompanionType] ?? trip.companionType)
  }
  return parts.join(" · ")
}

function formatVisitInfo(place: TripPlaceDetail): string {
  return place.visitTime ? place.visitTime.slice(0, 5) : "시간 미설정"
}

export function TripPlacesForm() {
  const { tripId } = useParams<{ tripId: string }>()
  const navigate = useNavigate()

  const [trip, setTrip] = useState<TripDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [removing, setRemoving] = useState(false)

  const [searchOpen, setSearchOpen] = useState(false)
  const [keyword, setKeyword] = useState("")
  const [results, setResults] = useState<PlaceSearchItem[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [pendingPlaceId, setPendingPlaceId] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editingTime, setEditingTime] = useState("")
  const [savingEdit, setSavingEdit] = useState(false)

  const refreshTrip = useCallback(async () => {
    if (!tripId) return
    try {
      const detail = await getTripDetail(tripId)
      setTrip(detail)
      setLoadError(null)
    } catch (err) {
      setLoadError(toErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [tripId])

  useEffect(() => {
    refreshTrip()
  }, [refreshTrip])

  useEffect(() => {
    if (!searchOpen || !keyword.trim()) {
      setResults([])
      setSearchError(null)
      return
    }
    let cancelled = false
    setSearching(true)
    const handle = setTimeout(() => {
      searchPlaces(keyword.trim().slice(0, SEARCH_KEYWORD_MAX_LENGTH), trip?.regionId)
        .then((items) => {
          if (cancelled) return
          setResults(items)
          setSearchError(null)
        })
        .catch((err) => {
          if (cancelled) return
          setSearchError(toErrorMessage(err))
        })
        .finally(() => {
          if (cancelled) return
          setSearching(false)
        })
    }, SEARCH_DEBOUNCE_MS)
    return () => {
      cancelled = true
      clearTimeout(handle)
    }
  }, [keyword, searchOpen, trip?.regionId])

  const handleDrop = useCallback(
    async (fromIndex: number, toIndex: number) => {
      if (!trip || !tripId) return
      const reordered = applyReorder(sortPlacesForDisplay(trip.places), fromIndex, toIndex)
      const withNewOrder = withVisitOrder(reordered)
      setTrip({ ...trip, places: withNewOrder })
      setActionError(null)
      try {
        await reorderTripPlaces(
          tripId,
          withNewOrder.map((p) => ({ tripPlaceId: p.tripPlaceId, visitOrder: p.visitOrder })),
        )
        await refreshTrip()
      } catch (err) {
        setActionError(toErrorMessage(err))
        await refreshTrip()
      }
    },
    [trip, tripId, refreshTrip],
  )

  const { dragIndex, pointerPos, gripProps, isDragging, isDropTarget } = useLongPressReorder(handleDrop)

  async function handleAddSearchResult(placeId: string, visitTime: string | null) {
    if (!tripId) return
    setPendingPlaceId(placeId)
    setActionError(null)
    try {
      await addPlaceToTrip(tripId, placeId, visitTime)
      await refreshTrip()
    } catch (err) {
      setActionError(toErrorMessage(err))
    } finally {
      setPendingPlaceId(null)
    }
  }

  async function handleRemove(tripPlaceId: string) {
    setActionError(null)
    setRemoving(true)
    try {
      await removeTripPlace(tripPlaceId)
      await refreshTrip()
    } catch (err) {
      setActionError(toErrorMessage(err))
    } finally {
      setRemoving(false)
    }
  }

  function startEdit(place: TripPlaceDetail) {
    setActionError(null)
    setEditingId(place.tripPlaceId)
    setEditingTime(place.visitTime ?? "")
  }

  function cancelEdit() {
    setEditingId(null)
    setEditingTime("")
  }

  async function handleSaveEdit() {
    if (!editingId) return
    setSavingEdit(true)
    setActionError(null)
    try {
      await updateTripPlaceVisit(editingId, { visitTime: editingTime || null })
      await refreshTrip()
      setEditingId(null)
      setEditingTime("")
    } catch (err) {
      setActionError(toErrorMessage(err))
    } finally {
      setSavingEdit(false)
    }
  }

  function handleGoToAnalysis() {
    if (!tripId) return
    setSubmitting(true)
    // STEP3 완료 후 방문 목적을 먼저 받던 중간 화면(TripPurposeForm)을 거치지 않고
    // 바로 분석 로딩 화면으로 간다 — 그 화면이 모으던 목적 데이터는 STEP4/STEP6 어디서도
    // 읽히지 않았고, "대안 찾기"에서 그 장소 하나만 물어보는 화면(RecommendationPurpose)이
    // 이미 따로 있어 중복이었다(2026-09-16, 코드 리뷰로 확인).
    navigate(`/trips/${tripId}/analysis`)
  }

  if (loading) {
    return (
      <div className="flex flex-1 flex-col">
        <StepHeader title="내 여행 일정 만들기" step={2} totalSteps={2} />
        <div className="flex flex-1 items-center justify-center text-[13px] text-ink-muted">
          불러오는 중...
        </div>
      </div>
    )
  }

  if (loadError || !trip) {
    return (
      <div className="flex flex-1 flex-col">
        <StepHeader title="내 여행 일정 만들기" step={2} totalSteps={2} />
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
          <p className="text-[13px] font-medium text-congestion-high">
            {loadError ?? "일정을 찾을 수 없습니다."}
          </p>
        </div>
      </div>
    )
  }

  const addedPlaceIds = new Set(trip.places.map((p) => p.placeId))
  const displayPlaces = sortPlacesForDisplay(trip.places)
  const draggedPlace = dragIndex !== null ? displayPlaces[dragIndex] : null

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      <StepHeader title="내 여행 일정 만들기" step={2} totalSteps={2} />

      <div className="flex items-center justify-between py-2 pl-8 pr-5">
        <p className="text-[12px] font-medium text-ink-muted">{formatConditionSummary(trip)}</p>
        <button
          className="text-[12px] font-bold text-primary"
          onClick={() => navigate(`/trips/${tripId}/conditions`)}
        >
          조건 수정
        </button>
      </div>

      <div className="flex flex-1 flex-col overflow-y-auto px-4">
        <button
          onClick={() => setSearchOpen(true)}
          className="flex h-[52px] w-full items-center gap-2.5 rounded-[var(--radius-field)] border-[0.667px] border-line bg-surface px-4 text-left"
        >
          <Search size={18} className="shrink-0 text-ink-faint" />
          <span className="text-[14px] text-ink-ghost">관광지 검색해서 추가</span>
        </button>

        <div className="flex items-center justify-between pt-4">
          <p className="text-[13px] font-bold text-ink">
            내 일정 <span className="text-primary">{trip.places.length}</span>곳
          </p>
          <p className="text-[11px] font-medium text-ink-faint">≡ 길게 눌러 순서 변경</p>
        </div>

        <div className="flex flex-col gap-2 pt-2">
          {trip.places.length === 0 && (
            <p className="py-6 text-center text-[13px] text-ink-muted">
              아직 등록된 장소가 없어요. 위에서 검색해서 추가해 보세요.
            </p>
          )}
          {displayPlaces.map((place, index) => {
            const canDrag = !place.visitTime
            const dragging = isDragging(index)
            const dropTarget = isDropTarget(index)
            const isEditing = editingId === place.tripPlaceId
            return (
              <div
                key={place.tripPlaceId}
                data-row-index={index}
                className={[
                  "flex items-center gap-3 rounded-[var(--radius-field)] bg-surface p-3.5 shadow-[var(--shadow-card)] transition-[opacity,box-shadow]",
                  dragging ? "opacity-50" : "",
                  dropTarget ? "ring-2 ring-primary/40" : "",
                ].join(" ")}
              >
                {isEditing ? (
                  <>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[14px] font-bold text-ink">{place.name}</p>
                      <input
                        type="time"
                        value={editingTime}
                        onChange={(e) => setEditingTime(e.target.value)}
                        className="mt-1 h-9 w-full rounded-[10px] border-[0.667px] border-line bg-surface px-2.5 text-[13px] text-ink outline-none"
                      />
                    </div>
                    <button
                      onClick={cancelEdit}
                      disabled={savingEdit}
                      className="shrink-0 text-[12px] font-semibold text-ink-faint disabled:opacity-50"
                    >
                      취소
                    </button>
                    <button
                      onClick={() => void handleSaveEdit()}
                      disabled={savingEdit}
                      className="shrink-0 text-[12px] font-bold text-primary disabled:opacity-50"
                    >
                      {savingEdit ? "저장 중..." : "저장"}
                    </button>
                  </>
                ) : (
                  <>
                    <Grip
                      size={16}
                      {...(canDrag ? gripProps(index) : {})}
                      className={`shrink-0 ${canDrag ? "cursor-grab text-ink-ghost" : "cursor-default text-ink-ghost/30"}`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[14px] font-bold text-ink">{place.name}</p>
                      <p className="text-[11px] font-medium text-ink-faint">{formatVisitInfo(place)}</p>
                    </div>
                    <button
                      onClick={() => startEdit(place)}
                      aria-label="방문 시간 수정"
                      className="shrink-0 text-ink-ghost hover:text-ink-soft"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      onClick={() => handleRemove(place.tripPlaceId)}
                      aria-label="장소 삭제"
                      className="shrink-0 text-ink-ghost hover:text-congestion-high"
                    >
                      <Close size={16} />
                    </button>
                  </>
                )}
              </div>
            )
          })}
        </div>

        <button
          onClick={() => navigate(`/trips/${tripId}/places/custom`)}
          className="mt-3 flex h-[46px] w-full items-center justify-center rounded-[var(--radius-field)] border-[0.667px] border-dashed border-line-chip text-[13px] font-semibold text-ink-muted"
        >
          + 목록에 없는 장소 직접 추가
        </button>

        <div className="mt-3 flex h-[74px] items-center justify-center rounded-[var(--radius-field)] border-[0.667px] border-dashed border-line bg-surface-sunken">
          <p className="text-[12px] font-medium text-ink-ghost">지도 영역 (준비 중)</p>
        </div>
        <div className="h-3" />
      </div>

      <div className="border-t-[0.667px] border-line-soft bg-surface/95 px-4 pb-6 pt-3">
        {actionError && (
          <p className="pb-2 text-center text-[12px] font-medium text-congestion-high">{actionError}</p>
        )}
        <p className="px-1 pb-2.5 text-[12px] text-ink-soft">
          총 <span className="font-bold text-ink">{trip.places.length}곳</span>
        </p>
        <div className="flex gap-2.5">
          {/* 추가/삭제/순서변경이 모두 즉시 서버에 저장되므로 "저장" 동작은 따로 없다 — 나가기만 한다. */}
          <Button
            variant="ghost"
            className="shrink-0"
            disabled={removing}
            onClick={() => navigate("/bookmarks")}
          >
            나가기
          </Button>
          <Button
            block
            loading={submitting}
            disabled={trip.places.length < 1}
            onClick={handleGoToAnalysis}
          >
            내 일정 점검하기
          </Button>
        </div>
      </div>

      {searchOpen && (
        <SearchBottomSheet
          keyword={keyword}
          onKeywordChange={setKeyword}
          onClose={() => setSearchOpen(false)}
          results={results}
          searching={searching}
          searchError={searchError}
          addedPlaceIds={addedPlaceIds}
          pendingPlaceId={pendingPlaceId}
          onAdd={handleAddSearchResult}
          onAddCustom={() => navigate(`/trips/${tripId}/places/custom`)}
        />
      )}

      {draggedPlace && pointerPos && (
        <div
          style={{
            position: "fixed",
            left: pointerPos.x,
            top: pointerPos.y,
            transform: "translate(-24px, -50%) rotate(-2deg)",
            pointerEvents: "none",
          }}
          className="z-40 flex w-[240px] items-center gap-3 rounded-[var(--radius-field)] bg-surface p-3.5 shadow-[0_16px_32px_rgba(16,24,48,0.28)] ring-2 ring-primary/50"
        >
          <Grip size={16} className="shrink-0 text-ink-ghost" />
          <p className="truncate text-[14px] font-bold text-ink">{draggedPlace.name}</p>
        </div>
      )}
    </div>
  )
}
