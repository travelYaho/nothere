/**
 * 남은 혼잡 장소 재점검
 */
import { useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { CongestionCard } from "@/components/common/cards"
import { Button } from "@/components/common/primitives"
import { FlowHeader } from "@/components/layout/navigation"
import { toUiCongestion, useRemaining } from "@/features/recommendation"

export default function RemainingCongested() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { data, loading, error, load } = useRemaining(tripId)

  useEffect(() => {
    void load()
  }, [load])

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
                    navigate(`/trips/${tripId}/places/${item.tripPlaceId}/compare`)
                  }
                />
              ))}
            </div>
            <p className="text-[12px] text-ink-faint">
              대안 보기는 Part2 recommendation request 생성 후
              <code className="mx-1">?requestId=</code>
              와 함께 비교 화면으로 진입하세요.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
