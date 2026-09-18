/**
 * 대안 찾기 2/2 — 원래 장소 vs 추천 대안 비교
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { Button } from "@/components/common/primitives"
import { AlertDialog, BottomSheet } from "@/components/feedback/modals"
import { FlowHeader } from "@/components/layout/navigation"
import { AlternativeCandidateCard } from "@/features/recommendation/components/AlternativeCandidateCard"
import { OriginalPlaceBar } from "@/features/recommendation/components/OriginalPlaceBar"
import {
  applyReplacement,
  keepTripPlace,
  toUiCongestion,
  useAccessToken,
  useCompareFlow,
} from "@/features/recommendation"
import type { CompareCandidate } from "@/features/recommendation"
import { kakaoMapSearchUrl } from "@/features/recommendation/utils/compareFormat"

export default function CompareAlternatives() {
  const { tripId, tripPlaceId } = useParams()
  const [params] = useSearchParams()
  const requestId = params.get("requestId") ?? undefined
  const navigate = useNavigate()
  const token = useAccessToken()
  const { data, loading, error, load } = useCompareFlow(requestId)

  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [keeping, setKeeping] = useState(false)
  const [keepError, setKeepError] = useState<string | null>(null)
  const [pending, setPending] = useState<CompareCandidate | null>(null)
  const [applying, setApplying] = useState(false)
  const [applyError, setApplyError] = useState<string | null>(null)
  const [detail, setDetail] = useState<CompareCandidate | null>(null)

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!data) return
    const first = data.candidates.find((c) => c.isEligible) ?? data.candidates[0]
    setExpandedId((prev) => {
      if (prev && data.candidates.some((c) => c.candidateId === prev)) return prev
      return first?.candidateId ?? null
    })
  }, [data])

  const visible = data?.candidates.filter((c) => c.isEligible) ?? []
  const originalLevel = toUiCongestion(data?.originalPlace.congestionLevel)

  const goRemaining = () => {
    navigate(`/trips/${tripId}/remaining`)
  }

  const handleKeep = async () => {
    if (!tripPlaceId || keeping) return
    setKeeping(true)
    setKeepError(null)
    try {
      await keepTripPlace(tripPlaceId)
      goRemaining()
    } catch (e) {
      setKeepError(e instanceof Error ? e.message : "저장 실패")
    } finally {
      setKeeping(false)
    }
  }

  const handleApply = async () => {
    if (!tripPlaceId || !pending) return
    setApplying(true)
    setApplyError(null)
    try {
      await applyReplacement(token, tripPlaceId, pending.candidateId)
      setPending(null)
      goRemaining()
    } catch (e) {
      setApplyError(e instanceof Error ? e.message : "교체 실패")
    } finally {
      setApplying(false)
    }
  }

  const openMap = (placeName: string) => {
    window.open(kakaoMapSearchUrl(placeName), "_blank", "noopener,noreferrer")
  }

  return (
    <div className="relative flex min-h-screen flex-1 flex-col">
      <FlowHeader
        title="대안 찾기"
        step={2}
        totalSteps={2}
        progress={1}
        onBack={() => navigate(-1)}
      />

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-4">
        {loading && <p className="pt-2 text-[13px] text-ink-muted">가까운 대안을 찾는 중…</p>}
        {error && <p className="pt-2 text-[13px] text-congestion-high">{error}</p>}
        {!requestId && (
          <p className="pt-2 text-[13px] text-ink-muted">
            URL에 <code className="text-ink">?requestId=</code> 가 필요합니다.
          </p>
        )}
        {keepError && <p className="pt-2 text-[13px] text-congestion-high">{keepError}</p>}
        {applyError && <p className="pt-2 text-[13px] text-congestion-high">{applyError}</p>}

        {data && (
          <>
            <div className="pt-2">
              <OriginalPlaceBar
                name={data.originalPlace.name}
                level={originalLevel}
                travelMinutes={data.originalPlace.travelMinutes}
                keeping={keeping}
                onKeep={() => void handleKeep()}
              />
            </div>

            <div className="flex items-center justify-between px-1 pt-4">
              <p className="text-[14px] font-extrabold tracking-[-0.28px] text-ink">
                비슷한 경험의 가까운 대안{" "}
                <span className="text-primary">{visible.length}곳</span>
              </p>
              <p className="text-[11px] font-medium leading-[16.5px] text-ink-faint">추천순</p>
            </div>

            {visible.length === 0 && (
              <p className="pt-4 text-[13px] text-ink-muted">
                조건에 맞는 대안을 찾지 못했어요. 원래 일정을 유지할 수 있어요.
              </p>
            )}

            <div className="flex flex-col gap-2.5 pt-2">
              {visible.map((candidate, index) => {
                const hasDetail = Boolean(candidate.address || candidate.reasonText)
                return (
                  <AlternativeCandidateCard
                    key={candidate.candidateId}
                    candidate={candidate}
                    index={index}
                    expanded={candidate.candidateId === expandedId}
                    applying={applying && pending?.candidateId === candidate.candidateId}
                    originalTravelMinutes={data.originalPlace.travelMinutes}
                    onToggle={() =>
                      setExpandedId((prev) =>
                        prev === candidate.candidateId ? null : candidate.candidateId,
                      )
                    }
                    onChange={() => setPending(candidate)}
                    onMap={() => openMap(candidate.placeName)}
                    onDetail={hasDetail ? () => setDetail(candidate) : undefined}
                  />
                )
              })}
            </div>

            <p className="py-4 text-center text-[11px] leading-[16.5px] text-ink-ghost">
              예상 집중도는 방문 추이 기반 예측이며 실제와 다를 수 있습니다.
            </p>
          </>
        )}
      </div>

      <div className="shrink-0 border-t-[0.667px] border-line-soft bg-surface/95 px-4 pb-6 pt-3">
        <Button variant="ghost" block onClick={() => void handleKeep()} disabled={keeping}>
          {keeping ? "저장 중…" : "원래 일정 유지하기"}
        </Button>
      </div>

      <AlertDialog
        open={pending != null}
        title="장소를 교체할까요?"
        description={
          data && pending
            ? `${data.originalPlace.name} → ${pending.placeName} 으로 일정이 바뀝니다.`
            : undefined
        }
        confirmLabel={applying ? "적용 중…" : "교체하기"}
        onConfirm={() => void handleApply()}
        onCancel={() => {
          if (!applying) setPending(null)
        }}
      />

      <BottomSheet
        open={detail != null}
        title={detail?.placeName}
        onClose={() => setDetail(null)}
        footer={
          <Button variant="ghost" block onClick={() => setDetail(null)}>
            닫기
          </Button>
        }
      >
        {detail?.address && (
          <p className="text-[13px] leading-[19.5px] text-ink">{detail.address}</p>
        )}
        {detail?.reasonText && (
          <p className="mt-2 text-[13px] leading-[19.5px] text-ink-soft">{detail.reasonText}</p>
        )}
      </BottomSheet>
    </div>
  )
}
