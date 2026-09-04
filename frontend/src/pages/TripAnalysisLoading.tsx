/**
 * TripAnalysisLoading — "일정을 점검하고 있어요" 로딩 화면.
 * Figma: 여기말GO / node 48:2774 "일정 분석 로딩 화면"
 *
 * 정적 UI만 구현했다. 실제 혼잡도 분석(POST /trips/{tripId}/analysis)은
 * Part2(김도연)/Part3(홍수민) 담당 API라 제 백엔드엔 없다 — 그 API가 생기면
 * 여기서 호출하고 완료 후 결과 화면으로 navigate 하면 된다.
 */
import { useParams } from "react-router-dom"
import { Search } from "@/components/common/icons"
import { StepHeader } from "@/features/trips/components/StepHeader"

export default function TripAnalysisLoading() {
  const { tripId } = useParams<{ tripId: string }>()

  return (
    <div className="flex flex-1 flex-col">
      <StepHeader title="대안 찾기" step={1} totalSteps={2} />

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
      </div>
    </div>
  )
}
