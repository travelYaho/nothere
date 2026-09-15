/**
 * TripPlacesForm — STEP3 "내 여행 일정 만들기" (장소 등록) 화면.
 * Figma: 여기말GO / node 48:2979 "일정 등록" (리스트) + 48:3158 "검색 바텀 시트"
 * (검색바에 포커스를 주면 바텀시트가 뜨는, 같은 화면의 두 가지 상태다)
 *
 * "이동 X분"/"예상 이동 OO분" 처럼 장소 간 이동시간을 보여주는 부분은 구현하지
 * 않았다 — 그건 경로 계산(Part3 담당, STEP4~6)이 필요한 값이라 지금은 낼 수
 * 있는 실제 데이터가 없다. 지도 영역도 Figma 원본 주석 그대로 "준비 중" placeholder다.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Close, Grip, Search } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { StepHeader } from "@/features/trips/components/StepHeader"
import { SearchBottomSheet } from "@/features/trips/components/SearchBottomSheet"
import { getTripDetail } from "@/features/trips/api/tripsApi"
import {
  addPlaceToTrip,
  removeTripPlace,
  reorderTripPlaces,
  searchPlaces,
} from "@/features/trips/api/placesApi"
import { COMPANION_LABELS } from "@/features/trips/constants"
import type { CompanionType, PlaceSearchItem, TripDetailResponse, TripPlaceDetail } from "@/features/trips/types"
import { ApiError } from "@/types/api"

const SEARCH_DEBOUNCE_MS = 350
const LONG_PRESS_MS = 350
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

/**
 * 시간이 설정된 장소끼리만 오름차순으로 재배열하고, 그 장소들이 원래
 * 차지하던 자리(index)에 도로 끼워 넣는다 — 시간 미설정 장소는 드래그로
 * 옮긴 자리를 그대로 유지한 채(꾹 눌러 순서 변경 가능), 시간이 있는
 * 장소만 "빠른 시간대가 앞"이 되도록 자동 정렬하기 위해서다.
 */
function sortPlacesForDisplay(places: TripPlaceDetail[]): TripPlaceDetail[] {
  const result = [...places]
  const timedIndices: number[] = []
  result.forEach((place, index) => {
    if (place.visitTime) timedIndices.push(index)
  })
  const timedSorted = timedIndices
    .map((index) => result[index])
    .sort((a, b) => (a.visitTime! < b.visitTime! ? -1 : a.visitTime! > b.visitTime! ? 1 : 0))
  timedIndices.forEach((index, i) => {
    result[index] = timedSorted[i]
  })
  return result
}

export function TripPlacesForm() {
  const { tripId } = useParams<{ tripId: string }>()
  const navigate = useNavigate()

  const [trip, setTrip] = useState<TripDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [overIndex, setOverIndex] = useState<number | null>(null)
  const [pointerPos, setPointerPos] = useState<{ x: number; y: number } | null>(null)
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [searchOpen, setSearchOpen] = useState(false)
  const [keyword, setKeyword] = useState("")
  const [results, setResults] = useState<PlaceSearchItem[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [pendingPlaceId, setPendingPlaceId] = useState<string | null>(null)

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
    return () => {
      if (longPressTimer.current !== null) clearTimeout(longPressTimer.current)
    }
  }, [])

  useEffect(() => {
    if (!searchOpen || !keyword.trim()) {
      setResults([])
      setSearchError(null)
      return
    }
    let cancelled = false
    setSearching(true)
    const handle = setTimeout(() => {
      searchPlaces(keyword.trim(), trip?.regionId)
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
    try {
      await removeTripPlace(tripPlaceId)
      await refreshTrip()
    } catch (err) {
      setActionError(toErrorMessage(err))
    }
  }

  function clearLongPressTimer() {
    if (longPressTimer.current !== null) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
  }

  /**
   * 드래그 순서변경은 HTML5 네이티브 draggable 대신 포인터 이벤트로 직접
   * 구현했다 — 네이티브 drag&drop 은 터치스크린(모바일)에서 아예 동작하지
   * 않고, 데스크톱에서도 "누르고만 있기"로는 시작되지 않아 "길게 눌러 순서
   * 변경" UX와 맞지 않는다. 손잡이(Grip)를 일정 시간 누르고 있으면 드래그가
   * 시작되고, setPointerCapture 덕분에 손가락/마우스가 손잡이 밖으로 나가도
   * move/up 이벤트를 계속 받는다.
   */
  function handleGripPointerDown(index: number) {
    return (e: React.PointerEvent<SVGSVGElement>) => {
      e.currentTarget.setPointerCapture(e.pointerId)
      clearLongPressTimer()
      const { clientX, clientY } = e
      longPressTimer.current = setTimeout(() => {
        setDragIndex(index)
        setOverIndex(index)
        setPointerPos({ x: clientX, y: clientY })
      }, LONG_PRESS_MS)
    }
  }

  function handleGripPointerMove(e: React.PointerEvent<SVGSVGElement>) {
    if (dragIndex === null) return
    setPointerPos({ x: e.clientX, y: e.clientY })
    const el = document.elementFromPoint(e.clientX, e.clientY)
    const rowEl = el instanceof Element ? el.closest<HTMLElement>("[data-row-index]") : null
    if (!rowEl) return
    const idx = Number(rowEl.dataset.rowIndex)
    if (!Number.isNaN(idx)) setOverIndex(idx)
  }

  function handleGripPointerUp() {
    clearLongPressTimer()
    if (dragIndex !== null && overIndex !== null) {
      handleDrop(overIndex)
    } else {
      setDragIndex(null)
      setOverIndex(null)
    }
    setPointerPos(null)
  }

  function handleGripPointerCancel() {
    clearLongPressTimer()
    setDragIndex(null)
    setOverIndex(null)
    setPointerPos(null)
  }

  async function handleDrop(targetIndex: number) {
    if (dragIndex === null || dragIndex === targetIndex || !trip || !tripId) {
      setDragIndex(null)
      setOverIndex(null)
      return
    }
    const reordered = sortPlacesForDisplay(trip.places)
    const [moved] = reordered.splice(dragIndex, 1)
    reordered.splice(targetIndex, 0, moved)
    setDragIndex(null)
    setOverIndex(null)

    const withNewOrder = reordered.map((p, i) => ({ ...p, visitOrder: i + 1 }))
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
  }

  function handleGoToPurpose() {
    if (!tripId) return
    setSubmitting(true)
    // STEP3 완료 후 바로 분석으로 가지 않고, 등록된 장소마다 방문 목적을
    // 먼저 받는다(3/3 단계) — 그다음에 분석 로딩 화면으로 이어진다.
    navigate(`/trips/${tripId}/purpose`)
  }

  if (loading) {
    return (
      <div className="flex flex-1 flex-col">
        <StepHeader title="내 여행 일정 만들기" step={2} totalSteps={3} />
        <div className="flex flex-1 items-center justify-center text-[13px] text-ink-muted">
          불러오는 중...
        </div>
      </div>
    )
  }

  if (loadError || !trip) {
    return (
      <div className="flex flex-1 flex-col">
        <StepHeader title="내 여행 일정 만들기" step={2} totalSteps={3} />
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
      <StepHeader title="내 여행 일정 만들기" step={2} totalSteps={3} />

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
            const isDragging = dragIndex === index
            const isDropTarget = dragIndex !== null && overIndex === index && !isDragging
            return (
              <div
                key={place.tripPlaceId}
                data-row-index={index}
                className={[
                  "flex items-center gap-3 rounded-[var(--radius-field)] bg-surface p-3.5 shadow-[var(--shadow-card)] transition-[opacity,box-shadow]",
                  isDragging ? "opacity-50" : "",
                  isDropTarget ? "ring-2 ring-primary/40" : "",
                ].join(" ")}
              >
                <Grip
                  size={16}
                  onPointerDown={canDrag ? handleGripPointerDown(index) : undefined}
                  onPointerMove={canDrag ? handleGripPointerMove : undefined}
                  onPointerUp={canDrag ? handleGripPointerUp : undefined}
                  onPointerCancel={canDrag ? handleGripPointerCancel : undefined}
                  style={{ touchAction: "none" }}
                  className={`shrink-0 ${canDrag ? "cursor-grab text-ink-ghost" : "cursor-default text-ink-ghost/30"}`}
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-bold text-ink">{place.name}</p>
                  <p className="text-[11px] font-medium text-ink-faint">{formatVisitInfo(place)}</p>
                </div>
                <button onClick={() => handleRemove(place.tripPlaceId)} className="shrink-0 text-ink-ghost">
                  <Close size={16} />
                </button>
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
          <Button variant="ghost" className="w-[92px] shrink-0">
            임시 저장
          </Button>
          <Button
            block
            loading={submitting}
            disabled={trip.places.length < 1}
            onClick={handleGoToPurpose}
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
