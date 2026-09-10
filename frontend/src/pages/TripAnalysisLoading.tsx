/**
 * TripAnalysisLoading — "일정을 점검하고 있어요" 로딩 화면 (STEP4).
 * Figma: 여기말GO / node 48:2774 "일정 분석 로딩 화면"
 *
 * 진입 시 POST /trips/{tripId}/analysis 를 호출해 집중도 분석을 실행하고,
 * 완료되면 남은 혼잡 장소 확인 화면(STEP8)으로 이동한다.
 */
import { useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Search } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { FlowHeader } from "@/components/layout/navigation"
import { useRunAnalysis } from "@/features/recommendation"

export default function TripAnalysisLoading() {
  const { tripId } = useParams<{ tripId: string }>()
  const navigate = useNavigate()
  const { data, error, run } = useRunAnalysis(tripId)

  useEffect(() => {
    void run()
  }, [run])

  useEffect(() => {
    if (data && tripId) {
      navigate(`/trips/${tripId}/remaining`)
    }
  }, [data, tripId, navigate])

  return (
    <div className="flex flex-1 flex-col">
      <FlowHeader title="일정 점검" step={4} totalSteps={9} progress={4 / 9} />

      <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
        <span className="flex size-16 items-center justify-center rounded-full bg-primary/10">
          <Search size={28} className="text-primary" />
        </span>
        <h2 className="pt-6 text-[17px] font-extrabold text-ink">일정을 점검하고 있어요</h2>
        <p className="pt-1.5 text-[13px] leading-[21px] text-ink-muted">
          방문 예정일의 관광지 집중률
          <br />
          예측 정보를 확인하는 중 ...
        </p>
        <div className="w-60 pt-8">
          <div className="h-1 w-full overflow-hidden rounded-full bg-surface-chip">
            <div className="h-full w-2/3 animate-pulse rounded-full bg-primary" />
          </div>
        </div>
        {!tripId && (
          <p className="pt-8 text-[12px] text-congestion-high">tripId 를 찾을 수 없습니다.</p>
        )}
        {error && (
          <>
            <p className="pt-8 text-[12px] text-congestion-high">{error}</p>
            <div className="w-60 pt-4">
              <Button block onClick={() => void run()}>
                다시 시도
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
