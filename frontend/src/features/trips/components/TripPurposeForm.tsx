/**
 * TripPurposeForm — "방문 목적" 입력 화면 (STEP3 직후, 3/3 단계).
 * Figma: 여기말GO / node 48:2817 "대안 찾기" 화면의 레이아웃을 기반으로 하되,
 * 실제 쓰임(STEP3 완료 직후 모든 장소에 대해 다중선택으로 목적을 미리 받아
 * 두었다가 나중에 혼잡 분석/대안 추천에 활용)에 맞게 아래처럼 바꿨다.
 *
 * - 원본은 혼잡 판정된 장소 1건에 대한 단일선택+자유텍스트였지만, 여긴 아직
 *   분석 전이라 혼잡 배지가 없고, 백엔드(PUT /trip-places/{id}/purpose)가
 *   다중선택·자유텍스트 없음이라 그에 맞췄다.
 * - 장소가 여러 개면 한 화면씩 순서대로 넘어가며 각 장소의 목적을 저장한다.
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Button, Chip } from "@/components/common/primitives"
import { StepHeader } from "@/features/trips/components/StepHeader"
import { getTripDetail, listExperienceTags } from "@/features/trips/api/tripsApi"
import { getTripPlacePurpose, putTripPlacePurpose } from "@/features/trips/api/purposeApi"
import type { ExperienceTag, TripDetailResponse, TripPlaceDetail } from "@/features/trips/types"
import { ApiError } from "@/types/api"

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

function formatVisitInfo(place: TripPlaceDetail): string {
  const parts: string[] = []
  if (place.visitTime) parts.push(`${place.visitTime.slice(0, 5)} 방문 예정`)
  if (place.durationMinutes != null) parts.push(`체류 ${place.durationMinutes}분`)
  return parts.length ? parts.join(" · ") : "방문 시간 미설정"
}

export function TripPurposeForm() {
  const { tripId } = useParams<{ tripId: string }>()
  const navigate = useNavigate()

  const [trip, setTrip] = useState<TripDetailResponse | null>(null)
  const [tags, setTags] = useState<ExperienceTag[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [placeIndex, setPlaceIndex] = useState(0)
  const [selectedByPlace, setSelectedByPlace] = useState<Record<string, number[]>>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!tripId) return
    let cancelled = false

    async function load() {
      try {
        const [tripDetail, tagList] = await Promise.all([getTripDetail(tripId!), listExperienceTags()])
        if (cancelled) return
        setTrip(tripDetail)
        setTags(tagList)

        const entries = await Promise.all(
          tripDetail.places.map((p) =>
            getTripPlacePurpose(p.tripPlaceId)
              .then((res) => [p.tripPlaceId, res.purposeTags.map((t) => t.id)] as const)
              .catch(() => [p.tripPlaceId, []] as const),
          ),
        )
        if (cancelled) return
        setSelectedByPlace(Object.fromEntries(entries))
      } catch (err) {
        if (!cancelled) setLoadError(toErrorMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [tripId])

  const currentPlace = trip?.places[placeIndex]
  const currentSelected = currentPlace ? (selectedByPlace[currentPlace.tripPlaceId] ?? []) : []
  const isLastPlace = trip ? placeIndex === trip.places.length - 1 : true

  function toggleTag(tagId: number) {
    if (!currentPlace) return
    setSelectedByPlace((prev) => {
      const cur = prev[currentPlace.tripPlaceId] ?? []
      const next = cur.includes(tagId) ? cur.filter((id) => id !== tagId) : [...cur, tagId]
      return { ...prev, [currentPlace.tripPlaceId]: next }
    })
  }

  async function handleAdvance(tagIds: number[]) {
    if (!currentPlace || !tripId) return
    setSubmitting(true)
    setError(null)
    try {
      await putTripPlacePurpose(currentPlace.tripPlaceId, tagIds)
      if (isLastPlace) {
        navigate(`/trips/${tripId}/analysis`)
      } else {
        setPlaceIndex((i) => i + 1)
      }
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-1 flex-col">
        <StepHeader title="방문 목적" step={3} totalSteps={3} />
        <div className="flex flex-1 items-center justify-center text-[13px] text-ink-muted">
          불러오는 중...
        </div>
      </div>
    )
  }

  if (loadError || !trip) {
    return (
      <div className="flex flex-1 flex-col">
        <StepHeader title="방문 목적" step={3} totalSteps={3} />
        <div className="flex flex-1 items-center justify-center px-6 text-center text-[13px] font-medium text-congestion-high">
          {loadError ?? "일정을 찾을 수 없습니다."}
        </div>
      </div>
    )
  }

  if (trip.places.length === 0 || !currentPlace) {
    return (
      <div className="flex flex-1 flex-col">
        <StepHeader title="방문 목적" step={3} totalSteps={3} />
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
          <p className="text-[13px] text-ink-muted">등록된 장소가 없어요.</p>
          <Button onClick={() => navigate(`/trips/${tripId}/places`)}>장소 등록하러 가기</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <StepHeader title="방문 목적" step={3} totalSteps={3} />

      <div className="flex flex-1 flex-col overflow-y-auto px-5">
        <div className="flex items-center justify-between pt-2">
          <div className="flex flex-1 items-center gap-3 rounded-[var(--radius-field)] bg-surface p-3 shadow-[var(--shadow-card)]">
            <span className="size-11 shrink-0 rounded-[12px] bg-surface-chip" />
            <div className="min-w-0">
              <p className="truncate text-[14px] font-bold text-ink">{currentPlace.name}</p>
              <p className="text-[11px] font-medium text-ink-faint">{formatVisitInfo(currentPlace)}</p>
            </div>
          </div>
          <span className="pl-3 text-[12px] font-semibold text-ink-faint">
            {placeIndex + 1} / {trip.places.length}
          </span>
        </div>

        <h2 className="pt-5 text-[18px] font-extrabold leading-[24.75px] text-ink">
          이 장소에서 어떤 경험을
          <br />
          기대하시나요?
        </h2>

        {error && (
          <p className="mt-4 rounded-[var(--radius-field)] bg-congestion-high-bg px-4 py-3 text-[13px] font-medium text-congestion-high">
            {error}
          </p>
        )}

        <div className="flex flex-wrap gap-2 pb-6 pt-4">
          {tags.map((tag) => (
            <Chip
              key={tag.id}
              label={tag.name}
              selected={currentSelected.includes(tag.id)}
              onClick={() => toggleTag(tag.id)}
            />
          ))}
        </div>
      </div>

      <div className="border-t-[0.667px] border-line-soft bg-surface/95 px-4 pb-6 pt-3">
        <div className="flex gap-2.5">
          <Button
            variant="ghost"
            className="w-[92px] shrink-0"
            disabled={submitting}
            onClick={() => handleAdvance([])}
          >
            건너뛰기
          </Button>
          <Button block loading={submitting} onClick={() => handleAdvance(currentSelected)}>
            {isLastPlace ? "완료" : "다음"}
          </Button>
        </div>
      </div>
    </div>
  )
}
