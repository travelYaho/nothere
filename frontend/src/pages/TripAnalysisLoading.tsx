/**
 * TripAnalysisLoading — "일정을 점검하고 있어요" 로딩 화면.
 * Figma: 여기말GO / node 48:2774 "일정 분석 로딩 화면"
 *
 * 마운트 시 STEP4 집중도 분석(POST /trips/{tripId}/analysis)을 실행하고, 성공하면 결과를
 * 다시 조회하지 않고 그대로 들고 "일정 점검 결과" 화면(/remaining)으로 넘어간다. 실패하면
 * 이 화면에 머물며 재시도할 수 있게 한다.
 */
import { useCallback, useEffect, useRef } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Search } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { StepHeader } from "@/features/trips/components/StepHeader"
import { useRunAnalysis } from "@/features/recommendation"
import { useSession } from "@/store/sessionStore"

export default function TripAnalysisLoading() {
  const { tripId } = useParams<{ tripId: string }>()
  const navigate = useNavigate()
  const { run, error, loading } = useRunAnalysis(tripId)
  const { isLoading: sessionLoading } = useSession()

  // 화면을 떠난 뒤(뒤로가기 등) 늦게 도착한 응답이 엉뚱하게 navigate 시키지 않도록,
  // 그리고 StrictMode 이중 호출·연타로 분석 요청이 겹치지 않도록 두 ref로 막는다.
  const mountedRef = useRef(true)
  const inFlightRef = useRef(false)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const start = useCallback(() => {
    if (!tripId || inFlightRef.current) return
    inFlightRef.current = true
    void run().then((result) => {
      inFlightRef.current = false
      if (!mountedRef.current) return
      if (result) {
        navigate(`/trips/${tripId}/remaining`, { state: { analysis: result } })
      }
    })
  }, [tripId, run, navigate])

  useEffect(() => {
    // 세션(토큰) 로딩이 끝나기 전에 호출하면 항상 401로 실패하므로 기다렸다가 한 번만 부른다.
    if (sessionLoading) return
    start()
  }, [sessionLoading, start])

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
        {error && !loading && (
          <div className="flex flex-col items-center gap-3 pt-8">
            <p className="text-[13px] text-congestion-high">{error}</p>
            <Button onClick={start}>다시 시도</Button>
          </div>
        )}
      </div>
    </div>
  )
}
