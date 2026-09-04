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
  const parts: string[] = []
  if (place.visitTime) parts.push(place.visitTime.slice(0, 5))
  if (place.durationMinutes != null) parts.push(`체류 ${place.durationMinutes}분`)
  return parts.length ? parts.join(" · ") : "시간 미설정"
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
    if (!searchOpen || !keyword.trim()) {
      setResults([])
      setSearchError(null)
      return
    }
    setSearching(true)
    const handle = setTimeout(() => {
      searchPlaces(keyword.trim(), trip?.regionId)
        .then((items) => {
          setResults(items)
          setSearchError(null)
        })
        .catch((err) => setSearchError(toErrorMessage(err)))
        .finally(() => setSearching(false))
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(handle)
  }, [keyword, searchOpen, trip?.regionId])

  async function handleAddSearchResult(placeId: string) {
    if (!tripId) return
    setPendingPlaceId(placeId)
    setActionError(null)
    try {
      await addPlaceToTrip(tripId, placeId)
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

  async function handleDrop(targetIndex: number) {
    if (dragIndex === null || dragIndex === targetIndex || !trip || !tripId) {
      setDragIndex(null)
      return
    }
    const reordered = [...trip.places]
    const [moved] = reordered.splice(dragIndex, 1)
    reordered.splice(targetIndex, 0, moved)
    setDragIndex(null)

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

  function handleGoToAnalysis() {
    if (!tripId) return
    setSubmitting(true)
    navigate(`/trips/${tripId}/analysis`)
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
          {trip.places.map((place, index) => (
            <div
              key={place.tripPlaceId}
              draggable
              onDragStart={() => setDragIndex(index)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDrop(index)}
              className="flex items-center gap-3 rounded-[var(--radius-field)] bg-surface p-3.5 shadow-[var(--shadow-card)]"
            >
              <Grip size={16} className="shrink-0 cursor-grab text-ink-ghost" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[14px] font-bold text-ink">{place.name}</p>
                <p className="text-[11px] font-medium text-ink-faint">{formatVisitInfo(place)}</p>
              </div>
              <button onClick={() => handleRemove(place.tripPlaceId)} className="shrink-0 text-ink-ghost">
                <Close size={16} />
              </button>
            </div>
          ))}
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
    </div>
  )
}
