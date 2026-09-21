/**
 * AlternativeSearchLoading — "대안을 찾고 있어요" 로딩 화면.
 * 일정 점검 로딩과 같은 연출. 마운트 시 후보 탐색 + 경로 점수를 실행하고,
 * 성공하면 비교 화면으로 대체 이동한다. 후보가 없거나 실패하면 이 화면에 남는다.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { FlowLoadingView } from "@/components/layout/FlowLoadingView"
import { useTripRegionName } from "@/features/loadingTips/useTripRegionName"
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
  const regionName = useTripRegionName(tripId, !sessionLoading)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // 후보 0건은 오류가 아니라 정상적인 검색 결과다 — 같은 태그로 "다시 시도"해도 결과가
  // 안 바뀐다(반경 확대는 이미 create() 한 번 안에서 다 시도됨, 이슈7에서 확인). error와
  // 같은 빨간 경고+재시도로 보여주면 안 돼서 별도 상태로 관리한다(2026-09-19, develop
  // 병합 중 새로 생긴 이 화면에도 이슈7의 원칙을 그대로 적용).
  const [noCandidate, setNoCandidate] = useState(false)

  const [purposeTagIds] = useState<number[]>(
    () => (location.state as LocationState)?.purposeTagIds ?? [],
  )

  // navigate(-1)은 안 쓴다 — 이 화면에 직접 접근했으면(북마크 등) 목적 화면이 아닌 엉뚱한
  // 곳으로 갈 수 있고, 뒤로가기로 목적 화면이 다시 마운트되면 selected가 []로 초기화돼
  // 방금 고른 태그가 사라진다(2026-09-19, 코드 리뷰로 발견). 목적 화면 경로로 명시적으로
  // 이동하면서 지금 태그를 state로 같이 넘겨 복원할 수 있게 한다. 헤더의 뒤로가기
  // 화살표(onBack)와 "다른 목적 선택하기"(onNoticeAction) 둘 다 이 화면을 떠나 목적
  // 화면으로 돌아간다는 점은 같으므로 같은 함수를 쓴다 — 하나만 고치면 나머지가 다시
  // 어긋나는 일이 없게(리뷰로 onBack이 빠졌던 걸 발견, 2026-09-19).
  const goToPurpose = useCallback(() => {
    navigate(`/trips/${tripId}/places/${tripPlaceId}/purpose`, {
      replace: true,
      state: { purposeTagIds },
    })
  }, [navigate, tripId, tripPlaceId, purposeTagIds])

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
    setNoCandidate(false)
    void (async () => {
      try {
        const result = await create(purposeTagIds)
        if (!mountedRef.current) return
        if (result.status !== "success" || result.candidateCount === 0) {
          setNoCandidate(true)
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
      notice={noCandidate ? "이 조건에 맞는 대안을 찾지 못했어요. 다른 목적을 선택해 주세요." : null}
      noticeActionLabel="다른 목적 선택하기"
      onNoticeAction={goToPurpose}
      loading={loading}
      tipRegionName={regionName}
      onRetry={start}
      onBack={goToPurpose}
    />
  )
}
