/**
 * STEP5·6 — 방문 목적 선택 후 대안 후보를 탐색한다.
 */
import { useEffect, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { Button, Chip } from "@/components/common/primitives"
import { FlowHeader } from "@/components/layout/navigation"
import { fetchAnalysis, useExperienceTags } from "@/features/recommendation"
import { useAccessToken } from "@/features/recommendation/hooks/usePart3"

type LocationState = { purposeTagIds?: number[] } | null

export default function RecommendationPurpose() {
  const { tripId, tripPlaceId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const token = useAccessToken()
  const { tags, loading: tagsLoading } = useExperienceTags()
  // AlternativeSearchLoading에서 "다른 목적 선택하기"로 돌아올 때 방금 고른 태그를
  // state로 함께 보낸다 — 그게 있으면 초기 선택값으로 복원한다. 없으면(STEP3에서 처음
  // 들어오는 정상 경로) 빈 배열로 시작한다(2026-09-19, 코드 리뷰로 발견 — 이 복원이
  // 없으면 되돌아올 때마다 선택이 초기화됐다).
  const [selected, setSelected] = useState<number[]>(
    () => (location.state as LocationState)?.purposeTagIds ?? [],
  )
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

  // 실제 검색(create + scoreRoutes)과 후보 0건 처리는 AlternativeSearchLoading으로 옮겼다
  // (일정 점검의 TripAnalysisLoading과 같은 패턴) — 이 화면은 태그만 고르고 넘어간다. 그
  // 결과로 "검색 중 태그를 바꿔서 화면이 엉뚱하게 보이는" 경쟁 상태도 구조적으로 사라진다
  // (여기서 대기하지 않고 곧장 다른 화면으로 이동하므로).
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
        // navigate(-1)이 아니라 점검 결과 화면으로 명시 이동한다 — "검색(후보없음)→목적
        // 복원"을 거친 뒤에는 방문 기록에 이 화면이 두 번 쌓일 수 있어(그 자체는 이번에
        // 해결한 범위가 아님), -1이 어디로 갈지 예측하기 어렵다. 사용자 입장에서 이
        // 화면의 뒤로가기는 항상 "일정 점검 결과로 돌아간다"여야 한다고 정했다
        // (2026-09-19, 코드 리뷰 논의로 결정).
        onBack={() => navigate(`/trips/${tripId}/remaining`)}
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
