/**
 * TripAnalysisLoading — "일정을 점검하고 있어요" 로딩 화면.
 * Figma: 여기말GO / node 48:2774 "일정 분석 로딩 화면"
 *
 * 마운트 시 STEP4 집중도 분석(POST /trips/{tripId}/analysis)을 실행하고, 성공하면 결과를
 * 다시 조회하지 않고 그대로 들고 "일정 점검 결과" 화면(/remaining)으로 넘어간다. 실패하면
 * 이 화면에 머물며 재시도할 수 있게 한다.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { FlowLoadingView } from "@/components/layout/FlowLoadingView"
import { useRunAnalysis } from "@/features/recommendation"
import { useSession } from "@/store/sessionStore"

/**
 * 실제 분석은 단일 요청(POST)이라 백엔드가 진행률을 내려주지 않는다 — 그래서 진행
 * 상황을 사실적으로 "느끼게" 하려고, 대기 중 일정 간격으로 단계 문구/진행폭만
 * 앞으로 넘기는 연출을 쓴다(실제 진행률 계측은 아님).
 */
const ANALYSIS_STEPS = [
  { label: "장소별 혼잡도 확인 중...", progress: 35 },
  { label: "이동 동선 계산 중...", progress: 68 },
  { label: "일정 최종 정리 중...", progress: 92 },
] as const
const STEP_INTERVAL_MS = 3000

export default function TripAnalysisLoading() {
  const { tripId } = useParams<{ tripId: string }>()
  const navigate = useNavigate()
  const { run, error, loading } = useRunAnalysis(tripId)
  const { isLoading: sessionLoading } = useSession()
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (!loading) return
    setStepIndex(0)
    const id = setInterval(() => {
      setStepIndex((i) => (i < ANALYSIS_STEPS.length - 1 ? i + 1 : i))
    }, STEP_INTERVAL_MS)
    return () => clearInterval(id)
  }, [loading])

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
        // 로딩은 한 번 지나가면 다시 볼 필요 없는 화면 — 뒤로가기로 재진입해서
        // 분석이 또 실행되지 않도록 히스토리에서 이 화면을 결과 화면으로 대체한다.
        navigate(`/trips/${tripId}/remaining`, { state: { analysis: result }, replace: true })
      }
    })
  }, [tripId, run, navigate])

  useEffect(() => {
    // 세션(토큰) 로딩이 끝나기 전에 호출하면 항상 401로 실패하므로 기다렸다가 한 번만 부른다.
    if (sessionLoading) return
    start()
  }, [sessionLoading, start])

  return (
    <FlowLoadingView
      headerTitle="일정 점검"
      headerProgress={4 / 9}
      title="일정을 점검하고 있어요"
      steps={ANALYSIS_STEPS}
      stepIndex={stepIndex}
      missingIdMessage={tripId ? undefined : "tripId 를 찾을 수 없습니다."}
      error={error}
      loading={loading}
      onRetry={start}
    />
  )
}
