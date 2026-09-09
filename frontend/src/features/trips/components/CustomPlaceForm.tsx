/**
 * CustomPlaceForm — "장소 직접 추가" 화면.
 * Figma: 여기말GO / node 48:3842 (프레임 자체 이름은 "여행 조건 온보딩"으로
 * 잘못 붙어 있지만 실제 내용은 장소 직접 추가 폼이다 — 사용자 확인받음)
 *
 * "예상 대기시간" 칩의 "90분 이상"은 명세에 정확한 분 단위가 없어 120분으로
 * 잠정 매핑했다 — 실제 값이 정해지면 EXTRA_WAIT_OPTIONS 만 바꾸면 된다.
 */
import { useEffect, useState, type FormEvent } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Button, Chip } from "@/components/common/primitives"
import { FieldLabel, TextInput } from "@/components/common/inputs"
import { StepHeader } from "@/features/trips/components/StepHeader"
import { addCustomPlaceToTrip } from "@/features/trips/api/placesApi"
import { listExperienceTags } from "@/features/trips/api/tripsApi"
import type { ExperienceTag } from "@/features/trips/types"
import { ApiError } from "@/types/api"

const WAIT_OPTIONS: { label: string; value: number }[] = [
  { label: "30분", value: 30 },
  { label: "60분", value: 60 },
  { label: "90분", value: 90 },
  { label: "90분 이상", value: 120 },
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

export function CustomPlaceForm() {
  const { tripId } = useParams<{ tripId: string }>()
  const navigate = useNavigate()

  const [tags, setTags] = useState<ExperienceTag[]>([])
  const [loadingTags, setLoadingTags] = useState(true)

  const [name, setName] = useState("")
  const [categoryTagId, setCategoryTagId] = useState<number | null>(null)
  const [address, setAddress] = useState("")
  const [waitMinutes, setWaitMinutes] = useState<number | null>(null)

  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    listExperienceTags()
      .then((list) => !cancelled && setTags(list))
      .catch((err) => !cancelled && setError(toErrorMessage(err)))
      .finally(() => !cancelled && setLoadingTags(false))
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (!tripId) return
    if (!name.trim()) return setError("장소 이름을 입력해 주세요.")
    if (categoryTagId === null) return setError("분류를 선택해 주세요.")
    if (!address.trim()) return setError("주소를 입력해 주세요.")

    setSubmitting(true)
    try {
      await addCustomPlaceToTrip(tripId, {
        name: name.trim(),
        categoryTagId,
        address: address.trim(),
        expectedWaitMinutes: waitMinutes,
      })
      navigate(`/trips/${tripId}/places`)
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col overflow-hidden">
      <StepHeader title="장소 직접 추가" step={2} totalSteps={3} onBack={() => navigate(-1)} />

      <div className="flex flex-1 flex-col overflow-y-auto px-5">
        <p className="whitespace-pre-line pt-2 text-[12px] leading-[15px] text-ink-soft">
          {"검색 목록에 없는 장소를 직접 등록할 수 있어요. 등록한 장소는 집중도 예측 없이 일정에만 추가돼요."}
        </p>

        <div className="pt-4">
          <FieldLabel required>장소 이름</FieldLabel>
          <TextInput
            placeholder="예) 유성푸르지오시티"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="pt-5">
          <FieldLabel required>분류</FieldLabel>
          <div className="flex flex-wrap gap-2">
            {loadingTags && <p className="text-[13px] text-ink-muted">불러오는 중...</p>}
            {tags.map((tag) => (
              <Chip
                key={tag.id}
                label={tag.name}
                selected={categoryTagId === tag.id}
                onClick={() => setCategoryTagId(tag.id)}
              />
            ))}
          </div>
        </div>

        <div className="pt-5">
          <FieldLabel required>주소</FieldLabel>
          <TextInput
            placeholder="예) 대전 유성구 대학로 291"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
        </div>

        <div className="pt-5 pb-4">
          <FieldLabel>예상 대기시간</FieldLabel>
          <div className="flex flex-wrap gap-2">
            {WAIT_OPTIONS.map((opt) => (
              <Chip
                key={opt.value}
                label={opt.label}
                selected={waitMinutes === opt.value}
                onClick={() => setWaitMinutes((prev) => (prev === opt.value ? null : opt.value))}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="border-t-[0.667px] border-line-soft bg-surface/95 px-4 pb-6 pt-3">
        {error && <p className="pb-2 text-center text-[12px] font-medium text-congestion-high">{error}</p>}
        <Button type="submit" block loading={submitting}>
          일정에 추가
        </Button>
      </div>
    </form>
  )
}
