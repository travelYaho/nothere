/**
 * AlternativeSearchLoading — "대안을 찾고 있어요" 로딩 화면.
 * 일정 점검 로딩과 같은 연출. 마운트 시 후보 탐색 + 경로 점수를 실행하고,
 * 성공하면 비교 화면으로 대체 이동한다. 후보가 없거나 실패하면 이 화면에 남는다.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { FlowLoadingView } from "@/components/layout/FlowLoadingView"
import { scoreRoutes, useAccessToken, useCreateRecommendationRequest } from "@/features/recommendation"
import { useSession } from "@/store/sessionStore"

const SEARCH_STEPS = [
  { label: "방문 목적에 맞는 장소 찾는 중...", progress: 35 },
  { label: "이동 동선 계산 중...", progress: 68 },
  { label: "대안 정리 중...", progress: 92 },
] as const
const STEP_INTERVAL_MS = 3000

type LocationState = {
  purposeTagIds?: number[]
} | null

export default function AlternativeSearchLoading() {
  const { tripId, tripPlaceId } = useParams<{ tripId: string; tripPlaceId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const token = useAccessToken()
  const { isLoading: sessionLoading } = useSession()
  const { create } = useCreateRecommendationRequest(tripPlaceId)
  const [stepIndex, setStepIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [purposeTagIds] = useState<number[]>(
    () => (location.state as LocationState)?.purposeTagIds ?? [],
  )

  useEffect(() => {
    if (!loading) return
    setStepIndex(0)
    const id = setInterval(() => {
      setStepIndex((i) => (i < SEARCH_STEPS.length - 1 ? i + 1 : i))
    }, STEP_INTERVAL_MS)
    return () => clearInterval(id)
  }, [loading])

  const mountedRef = useRef(true)
  const inFlightRef = useRef(false)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const start = useCallback(() => {
    if (!tripId || !tripPlaceId || inFlightRef.current) return
    inFlightRef.current = true
    setLoading(true)
    setError(null)
    void (async () => {
      try {
        const result = await create(purposeTagIds)
        if (!mountedRef.current) return
        if (result.status !== "success" || result.candidateCount === 0) {
          setError("가까운 대안을 찾지 못했어요.")
          return
        }
        await scoreRoutes(token, result.requestId)
        if (!mountedRef.current) return
        navigate(
          `/trips/${tripId}/places/${tripPlaceId}/compare?requestId=${result.requestId}`,
          { state: { scored: true }, replace: true },
        )
      } catch (e) {
        if (!mountedRef.current) return
        setError(e instanceof Error ? e.message : "대안 후보 탐색 실패")
      } finally {
        inFlightRef.current = false
        if (mountedRef.current) setLoading(false)
      }
    })()
  }, [tripId, tripPlaceId, create, purposeTagIds, token, navigate])

  useEffect(() => {
    if (sessionLoading) return
    start()
  }, [sessionLoading, start])

  const missing =
    !tripId || !tripPlaceId ? "일정 또는 장소를 찾을 수 없습니다." : undefined

  return (
    <FlowLoadingView
      headerTitle="대안 찾기"
      headerProgress={5 / 9}
      title="대안을 찾고 있어요"
      steps={SEARCH_STEPS}
      stepIndex={stepIndex}
      missingIdMessage={missing}
      error={error}
      loading={loading}
      onRetry={start}
    />
  )
}
