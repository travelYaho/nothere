/**
 * STEP5·6 — 방문 목적 선택 후 대안 후보를 탐색한다.
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Button, Chip } from "@/components/common/primitives"
import { FlowHeader } from "@/components/layout/navigation"
import { fetchAnalysis, useExperienceTags } from "@/features/recommendation"
import { useAccessToken } from "@/features/recommendation/hooks/usePart3"

export default function RecommendationPurpose() {
  const { tripId, tripPlaceId } = useParams()
  const navigate = useNavigate()
  const token = useAccessToken()
  const { tags, loading: tagsLoading } = useExperienceTags()
  const [selected, setSelected] = useState<number[]>([])
  const [placeName, setPlaceName] = useState<string>("")

  useEffect(() => {
    if (!tripId) return
    fetchAnalysis(token, tripId)
      .then((result) => {
        const item = result.items.find((i) => i.tripPlaceId === tripPlaceId)
        if (item) setPlaceName(item.placeName)
      })
      .catch(() => undefined)
  }, [tripId, tripPlaceId, token])

  const toggle = (id: number) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]))
  }

  const goSearch = (tagIds: number[]) => {
    navigate(`/trips/${tripId}/places/${tripPlaceId}/searching`, {
      state: { purposeTagIds: tagIds },
    })
  }

  return (
    <div className="relative flex flex-1 flex-col">
      <FlowHeader
        title="대안 찾기"
        step={1}
        totalSteps={2}
        progress={0.5}
        onBack={() => navigate(-1)}
      />
      <div className="flex flex-1 flex-col gap-4 px-5 pb-10 pt-2">
        <p className="text-[14px] font-bold text-ink">
          {placeName ? `${placeName} 대신` : "이 장소 대신"} 어떤 경험을 원하시나요?
        </p>
        <p className="text-[12px] text-ink-faint">
          선택하지 않아도 대안을 찾을 수 있어요. 여러 개를 고를 수 있습니다.
        </p>

        {tagsLoading && <p className="text-[13px] text-ink-muted">불러오는 중…</p>}

        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <Chip
              key={tag.id}
              label={tag.name}
              variant="multi"
              selected={selected.includes(tag.id)}
              onClick={() => toggle(tag.id)}
            />
          ))}
        </div>

        <div className="mt-auto flex flex-col gap-2 pt-4">
          <Button block onClick={() => goSearch(selected)}>
            대안 찾기
          </Button>
          <Button variant="text" onClick={() => goSearch([])}>
            건너뛰기
          </Button>
        </div>
      </div>
    </div>
  )
}
