/**
 * STEP5·6 — 방문 목적 선택 후 대안 후보를 탐색한다.
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Button, Chip } from "@/components/common/primitives"
import { FlowHeader } from "@/components/layout/navigation"
import {
  fetchAnalysis,
  useCreateRecommendationRequest,
  useExperienceTags,
} from "@/features/recommendation"
import { useAccessToken } from "@/features/recommendation/hooks/usePart3"

export default function RecommendationPurpose() {
  const { tripId, tripPlaceId } = useParams()
  const navigate = useNavigate()
  const token = useAccessToken()
  const { tags, loading: tagsLoading } = useExperienceTags()
  const { create, loading: creating, error } = useCreateRecommendationRequest(tripPlaceId)
  const [selected, setSelected] = useState<number[]>([])
  const [placeName, setPlaceName] = useState<string>("")
  // 대안 0건은 에러가 아니라 정상적인 검색 결과다 — compare 화면(scoreRoutes)으로 넘어가면
  // 그 화면은 "성공한 요청"만 상대한다고 가정해서 400을 그대로 맞는다(이슈7, 2026-09-18).
  // 여기서 멈추면 선택한 태그(selected)도 그대로 남아 재시도 시 다시 고를 필요가 없다.
  const [noCandidate, setNoCandidate] = useState(false)

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
    setNoCandidate(false)
  }

  const search = async (tagIds: number[]) => {
    // 새 검색을 시작하면 이전 결과(안내든 아니든)는 지운다 — 안 지우면 "후보 없음 →
    // 같은 조건으로 재검색 → 이번엔 네트워크 오류" 순서에서 이전 "후보 없음" 안내와 새
    // 오류가 동시에 보이는 문제가 있었다(2026-09-18, 코드 리뷰로 발견). 선택한 태그
    // (tagIds)는 그대로 넘겨 쓰므로 유지된다.
    setNoCandidate(false)
    try {
      const result = await create(tagIds)
      if (result.status === "no_candidate" || result.candidateCount === 0) {
        setNoCandidate(true)
        return
      }
      navigate(`/trips/${tripId}/places/${tripPlaceId}/compare?requestId=${result.requestId}`)
    } catch {
      // useCreateRecommendationRequest가 error 상태로 노출한다.
    }
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
          {/* 검색 중(creating)에는 태그를 못 바꾸게 막는다 — 안 막으면 A로 검색 중에 B로
              바꾼 뒤 A의 "후보 없음" 응답이 도착해도 화면엔 B가 선택된 채로 그 안내가
              뜬다(아직 검색하지도 않은 B가 후보 없는 것처럼 보임, 2026-09-18 코드 리뷰로
              발견). */}
          {tags.map((tag) => (
            <Chip
              key={tag.id}
              label={tag.name}
              variant="multi"
              selected={selected.includes(tag.id)}
              disabled={creating}
              onClick={() => toggle(tag.id)}
            />
          ))}
        </div>

        {error && <p className="text-[13px] text-congestion-high">{error}</p>}

        {noCandidate && (
          <div className="rounded-[var(--radius-field)] bg-surface-chip px-4 py-3">
            <p className="text-[13px] font-medium text-ink">
              이 조건에 맞는 대안을 찾지 못했어요. 다른 목적을 선택해 주세요.
            </p>
          </div>
        )}

        <div className="mt-auto flex flex-col gap-2 pt-4">
          {noCandidate ? (
            // 같은 태그·같은 반경으로 다시 검색해도 결과가 안 바뀐다 — 반경 확대(3km→5km)는
            // 이미 이번 요청 안에서 자동으로 다 시도된 뒤라(백엔드 service.py의
            // modes_to_try), "같은 조건으로 재시도"는 사실상 의미가 없다(2026-09-18, 코드
            // 리뷰로 발견). 태그를 바꾸면(toggle) noCandidate가 꺼지고 "대안 찾기" 버튼이
            // 다시 나타나므로, 여기서는 조건 변경을 유도하고 나가는 길만 제공한다.
            <Button
              variant="text"
              onClick={() => navigate(`/trips/${tripId}/remaining`)}
              disabled={creating}
            >
              점검 결과로 돌아가기
            </Button>
          ) : (
            <>
              <Button block loading={creating} onClick={() => search(selected)}>
                대안 찾기
              </Button>
              <Button variant="text" onClick={() => search([])} disabled={creating}>
                건너뛰기
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
