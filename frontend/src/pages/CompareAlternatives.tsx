/**
 * STEP7 — 원래 장소 vs Top3 대안 비교
 */
import { useEffect } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { RecommendCard } from "@/components/common/cards"
import { CongestionBadge } from "@/components/common/primitives"
import { FlowHeader } from "@/components/layout/navigation"
import { toUiCongestion, useCompareFlow } from "@/features/recommendation"

export default function CompareAlternatives() {
  const { tripId, tripPlaceId } = useParams()
  const [params] = useSearchParams()
  const requestId = params.get("requestId") ?? undefined
  const navigate = useNavigate()
  const { data, loading, error, load } = useCompareFlow(requestId)

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="relative flex flex-1 flex-col">
      <FlowHeader
        title="대안 비교"
        step={7}
        totalSteps={9}
        progress={7 / 9}
        onBack={() => navigate(-1)}
      />
      <div className="flex flex-1 flex-col gap-4 px-5 pb-10 pt-2">
        {loading && <p className="text-[13px] text-ink-muted">추천을 계산하는 중…</p>}
        {error && <p className="text-[13px] text-congestion-high">{error}</p>}
        {!requestId && (
          <p className="text-[13px] text-ink-muted">
            URL에 <code className="text-ink">?requestId=</code> 가 필요합니다.
          </p>
        )}

        {data && (
          <>
            <section className="rounded-[var(--radius-field)] border-[0.667px] border-[#eeaaaa] bg-surface px-4 py-3.5">
              <p className="text-[9px] font-bold tracking-[0.9px] text-congestion-high">ORIGINAL</p>
              <div className="mt-1 flex items-center justify-between gap-2">
                <p className="text-[15px] font-bold text-ink">{data.originalPlace.name}</p>
                <CongestionBadge level={toUiCongestion(data.originalPlace.congestionLevel)} />
              </div>
            </section>

            <p className="text-[13px] font-semibold text-ink-soft">추천 대안 Top {data.candidates.length}</p>
            <div className="flex flex-col gap-3">
              {data.candidates.map((c) => (
                <div key={c.candidateId} className="flex flex-col gap-2">
                  <RecommendCard
                    tag={`RANK ${c.rank ?? "-"} · 추가 ${c.extraMinutes ?? 0}분`}
                    title={c.placeName}
                    level={toUiCongestion(c.congestionLevel)}
                    onClick={() =>
                      navigate(
                        `/trips/${tripId}/places/${tripPlaceId}/preview?candidateId=${c.candidateId}`,
                      )
                    }
                  />
                  {c.reasonText && (
                    <p className="px-1 text-[12px] leading-[18px] text-ink-muted">{c.reasonText}</p>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
