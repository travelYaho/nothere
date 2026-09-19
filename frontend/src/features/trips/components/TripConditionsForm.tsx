/**
 * TripConditionsForm — STEP2 "여행 조건" 입력 폼.
 * Figma: 여기말GO / node 84:68 "여행 조건 온보딩 (이동 시간 x)"
 *
 * 디자인과 실제 구현이 갈라지는 지점 2가지:
 * 1. "방문 지역"이 시/도+구/군 2단계 셀렉트로 그려져 있지만, 백엔드 Region은
 *    id/name 뿐인 단일 레벨(서울특별시/부산광역시)이라 구/군 선택은 구현하지 않는다.
 * 2. "선호 경험" 라벨의 "최소 1개" 문구는 백엔드가 실제로 강제하는 규칙(2~3개,
 *    INVALID_PREFERRED_EXPERIENCE_COUNT)과 달라서, 화면 문구는 "2~3개"로 맞췄다.
 *
 * URL에 tripId 가 있으면 "조건 수정"(PATCH) 모드로 동작한다 — STEP3 화면의
 * "조건 수정" 링크가 이리로 온다. 없으면 새 여행 생성(POST) 모드다.
 */
import { useEffect, useState, type FormEvent } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Button, Chip } from "@/components/common/primitives"
import { DatePicker, FieldLabel, Select } from "@/components/common/inputs"
import { StepHeader } from "@/features/trips/components/StepHeader"
import {
  createTrip,
  getTripDetail,
  listExperienceTags,
  listRegions,
  updateTripConditions,
} from "@/features/trips/api/tripsApi"
import { COMPANION_LABELS } from "@/features/trips/constants"
import type { CompanionType, ExperienceTag, Region } from "@/features/trips/types"
import { toDateOnlyString } from "@/utils/date"
import { ApiError } from "@/types/api"

const MIN_PREFERRED_TAGS = 2
const MAX_PREFERRED_TAGS = 3

const COMPANION_OPTIONS = (Object.entries(COMPANION_LABELS) as [CompanionType, string][]).map(
  ([value, label]) => ({ value, label }),
)

const EXTRA_TIME_OPTIONS: { label: string; value: number | null }[] = [
  { label: "10분", value: 10 },
  { label: "20분", value: 20 },
  { label: "30분", value: 30 },
  { label: "경험 우선", value: null },
]

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

function parseDateOnly(value: string): Date {
  return new Date(`${value}T00:00:00`)
}

export function TripConditionsForm() {
  const navigate = useNavigate()
  const { tripId: editingTripId } = useParams<{ tripId: string }>()
  const isEditMode = Boolean(editingTripId)

  const [regions, setRegions] = useState<Region[]>([])
  const [experienceTags, setExperienceTags] = useState<ExperienceTag[]>([])
  const [loadingOptions, setLoadingOptions] = useState(true)
  const [optionsError, setOptionsError] = useState<string | null>(null)

  const [travelDate, setTravelDate] = useState<Date | undefined>()
  const [regionName, setRegionName] = useState<string | undefined>()
  const [companionType, setCompanionType] = useState<CompanionType | null>(null)
  const [extraTimeLimit, setExtraTimeLimit] = useState<number | null | undefined>(undefined)
  const [preferredTagIds, setPreferredTagIds] = useState<number[]>([])

  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    const loaders: Promise<unknown>[] = [
      listRegions().then((list) => !cancelled && setRegions(list)),
      listExperienceTags().then((list) => !cancelled && setExperienceTags(list)),
    ]
    if (isEditMode && editingTripId) {
      loaders.push(
        getTripDetail(editingTripId).then((trip) => {
          if (cancelled) return
          if (trip.travelDate) setTravelDate(parseDateOnly(trip.travelDate))
          setRegionName(trip.regionName)
          setCompanionType((trip.companionType as CompanionType) ?? null)
          setExtraTimeLimit(trip.extraTimeLimitMinutes)
          setPreferredTagIds(trip.preferredExperienceTagIds)
        }),
      )
    }
    Promise.all(loaders)
      .catch((err) => {
        if (!cancelled) setOptionsError(toErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoadingOptions(false)
      })
    return () => {
      cancelled = true
    }
  }, [isEditMode, editingTripId])

  function toggleTag(id: number) {
    setPreferredTagIds((prev) => {
      if (prev.includes(id)) return prev.filter((tagId) => tagId !== id)
      if (prev.length >= MAX_PREFERRED_TAGS) return prev
      return [...prev, id]
    })
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitError(null)

    if (!travelDate) return setSubmitError("여행 날짜를 선택해 주세요.")
    const region = regions.find((r) => r.name === regionName)
    if (!region) return setSubmitError("방문 지역을 선택해 주세요.")
    if (!companionType) return setSubmitError("동행 유형을 선택해 주세요.")
    if (extraTimeLimit === undefined) return setSubmitError("허용 추가 이동시간을 선택해 주세요.")
    if (preferredTagIds.length < MIN_PREFERRED_TAGS || preferredTagIds.length > MAX_PREFERRED_TAGS) {
      return setSubmitError(`선호 경험은 ${MIN_PREFERRED_TAGS}~${MAX_PREFERRED_TAGS}개 선택해 주세요.`)
    }

    setSubmitting(true)
    try {
      if (isEditMode && editingTripId) {
        await updateTripConditions(editingTripId, {
          travelDate: toDateOnlyString(travelDate),
          regionId: region.id,
          companionType,
          extraTimeLimitMinutes: extraTimeLimit,
          preferredExperienceTagIds: preferredTagIds,
        })
        navigate(`/trips/${editingTripId}/places`)
      } else {
        const trip = await createTrip({
          travelDate: toDateOnlyString(travelDate),
          regionId: region.id,
          companionType,
          extraTimeLimitMinutes: extraTimeLimit,
          preferredExperienceTagIds: preferredTagIds,
        })
        navigate(`/trips/${trip.tripId}/places`)
      }
    } catch (err) {
      setSubmitError(toErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col overflow-hidden">
      <StepHeader
        title="여행 조건"
        step={1}
        totalSteps={2}
        onBack={isEditMode ? () => navigate(-1) : undefined}
      />

      <div className="flex flex-1 flex-col overflow-y-auto px-5">
        <h2 className="pt-2 text-[19px] font-extrabold tracking-[-0.38px] text-ink">
          이번 여행 조건을 알려주세요
        </h2>

        {optionsError && (
          <p className="mt-4 rounded-[var(--radius-field)] bg-congestion-high-bg px-4 py-3 text-[13px] font-medium text-congestion-high">
            {optionsError}
          </p>
        )}

        <div className="pt-4">
          <FieldLabel required>여행 날짜</FieldLabel>
          <DatePicker value={travelDate} onChange={setTravelDate} />
        </div>

        <div className="pt-5">
          <FieldLabel required>방문 지역</FieldLabel>
          <Select
            value={regionName}
            placeholder={loadingOptions ? "불러오는 중..." : "지역 선택"}
            options={regions.map((r) => r.name)}
            disabled={loadingOptions}
            onChange={setRegionName}
          />
        </div>

        <div className="pt-5">
          <FieldLabel required>동행 유형</FieldLabel>
          <div className="flex flex-wrap gap-2">
            {COMPANION_OPTIONS.map((opt) => (
              <Chip
                key={opt.value}
                label={opt.label}
                selected={companionType === opt.value}
                onClick={() => setCompanionType(opt.value)}
              />
            ))}
          </div>
        </div>

        <div className="pt-5">
          <FieldLabel required>허용 추가 이동시간</FieldLabel>
          <div className="flex flex-wrap gap-2">
            {EXTRA_TIME_OPTIONS.map((opt) => (
              <Chip
                key={opt.label}
                label={opt.label}
                selected={extraTimeLimit === opt.value}
                onClick={() => setExtraTimeLimit(opt.value)}
              />
            ))}
          </div>
        </div>

        <div className="pt-5 pb-4">
          <FieldLabel
            required
            hint={`${MIN_PREFERRED_TAGS}~${MAX_PREFERRED_TAGS}개`}
            right={
              <span className="text-[12px] font-bold text-primary">
                {preferredTagIds.length} / {MAX_PREFERRED_TAGS}
              </span>
            }
          >
            선호 경험
          </FieldLabel>
          <div className="flex flex-wrap gap-2">
            {experienceTags.map((tag) => (
              <Chip
                key={tag.id}
                label={tag.name}
                selected={preferredTagIds.includes(tag.id)}
                onClick={() => toggleTag(tag.id)}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="border-t-[0.667px] border-line-soft bg-surface/95 px-4 pb-6 pt-3">
        {submitError && (
          <p className="pb-2 text-center text-[12px] font-medium text-congestion-high">{submitError}</p>
        )}
        <Button type="submit" block loading={submitting}>
          {isEditMode ? "조건 저장" : "여행 조건 등록"}
        </Button>
      </div>
    </form>
  )
}
