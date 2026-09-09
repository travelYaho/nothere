/**
 * 남은 혼잡 장소 재점검
 */
import { useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { CongestionCard } from "@/components/common/cards"
import { Button } from "@/components/common/primitives"
import { FlowHeader } from "@/components/layout/navigation"
import { toUiCongestion, useRemaining, useRunAnalysis } from "@/features/recommendation"

export default function RemainingCongested() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { data, loading, error, load } = useRemaining(tripId)
  const { run: runAnalysis } = useRunAnalysis(tripId)

  useEffect(() => {
    // 이 화면에 들어올 때마다 최신 집중도로 다시 분석한 뒤 남은 혼잡 장소를 불러온다.
    void runAnalysis().then(() => load())
  }, [runAnalysis, load])

  return (
    <div className="relative flex flex-1 flex-col">
      <FlowHeader
        title="남은 혼잡 점검"
        step={8}
        totalSteps={9}
        progress={8 / 9}
        onBack={() => navigate(-1)}
      />
      <div className="flex flex-1 flex-col gap-4 px-5 pb-10 pt-2">
        {loading && <p className="text-[13px] text-ink-muted">확인 중…</p>}
        {error && <p className="text-[13px] text-congestion-high">{error}</p>}

        {data && data.allResolved && (
          <>
            <p className="text-[14px] font-bold text-ink">모든 혼잡 장소를 해결했습니다.</p>
            <Button block onClick={() => navigate(`/trips/${tripId}/confirm`)}>
              최종 확정으로
            </Button>
          </>
        )}

        {data && !data.allResolved && (
          <>
            <p className="text-[13px] text-ink-muted">
              아직 {data.remainingCount}곳의 혼잡 장소가 남아 있습니다.
            </p>
            <div className="flex flex-col gap-3">
              {data.items.map((item) => (
                <CongestionCard
                  key={item.tripPlaceId}
                  time=""
                  place={item.placeName}
                  level={toUiCongestion(item.level)}
                  onAlternative={() =>
                    navigate(`/trips/${tripId}/places/${item.tripPlaceId}/purpose`)
                  }
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
