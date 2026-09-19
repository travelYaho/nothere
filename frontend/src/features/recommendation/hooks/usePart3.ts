import { useCallback, useEffect, useRef, useState } from "react"
import { useSession } from "@/store/sessionStore"
import { ApiError } from "@/types/api"
import {
  applyReplacement,
  confirmTrip,
  createShareLink,
  fetchPublicGuide,
  fetchRemainingCongested,
  fetchReplacementPreview,
  fetchScoredCandidates,
  fetchTripGuide,
  scoreRoutes,
} from "../api/part3Api"
import type {
  CompareCandidatesResponse,
  GuideResponse,
  RemainingCongestedResponse,
  ReplacementPreviewResponse,
} from "../types/part3"

/** 실제 Supabase 세션의 access token. 로그인 전이거나 세션 로딩 중이면 빈 문자열(백엔드 401). */
export function useAccessToken(): string {
  const { session } = useSession()
  return session?.access_token ?? ""
}

// score-routes는 후보 0건이면 code="NO_CANDIDATE"인 400을 낸다(그 외 "success"가 아닌
// 상태는 code="INVALID_REQUEST"로 남겨둠 — 백엔드 service.py::score_routes 참고). STEP5는
// 이제 후보 0건이면 이 화면으로 넘어오지 않지만(이슈7), 그 전에 만들어진 링크를 통한
// 직접 접근·새로고침은 여전히 이 경로를 탄다 — code로 "후보 없음"과 진짜 오류를 구분한다.
// 메시지 문자열로 구분하면 안 된다 — "success"가 아닌 모든 상태가 한때 같은 문구를 썼고,
// 문구가 바뀌면 이 구분 자체가 조용히 깨진다(2026-09-18, 코드 리뷰로 발견).

export function useCompareFlow(
  requestId: string | undefined,
  options?: { skipScoring?: boolean },
) {
  const token = useAccessToken()
  const [data, setData] = useState<CompareCandidatesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [noCandidate, setNoCandidate] = useState(false)
  // 서버가 주는 requestId 문자열만으로는 "몇 번째 시도"를 구분 못 한다 — 같은 requestId를
  // 두 번 조회했는데 첫 응답이 늦게 오거나, A→B→A로 왕복한 뒤 첫 A 응답이 오거나,
  // requestId가 사라진 뒤에도 이전 실행을 무효화 못 하는 문제가 있었다(2026-09-18, 코드
  // 리뷰로 발견). 그래서 매 load() 호출마다 값이 늘어나는 실행 번호로 "이게 아직 최신
  // 실행인지"를 판단한다 — requestId가 같아도 다르게 본다(단순 in-flight 불리언 가드보다
  // 넓은 경쟁 상태를 잡는다).
  const executionRef = useRef(0)
  const skipScoring = options?.skipScoring ?? false

  useEffect(() => {
    // 언마운트되면 이 훅 인스턴스가 갖고 있던 마지막 실행도 무효화한다 — 화면을 떠난 뒤
    // 늦게 도착한 응답이 이미 사라진 컴포넌트를 위해 상태를 갱신하지 않게 한다.
    return () => {
      executionRef.current += 1
    }
  }, [])

  const load = useCallback(async () => {
    const myExecution = ++executionRef.current
    // 이전 요청의 후보·오류·후보없음 상태가 새 상태와 함께 남아있으면 안 된다 —
    // requestId가 사라지는 조기 반환 분기보다 반드시 앞에 둬야 한다. 조기 반환 뒤에
    // 두면(이전 버전의 버그) "정상 조회 후 URL에서 requestId만 없어지는" 경우 이전
    // 후보·오류가 그대로 남았다(2026-09-18, 코드 리뷰로 발견).
    setData(null)
    setError(null)
    setNoCandidate(false)
    if (!requestId) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      if (!skipScoring) {
        await scoreRoutes(token, requestId)
      }
      const compared = await fetchScoredCandidates(token, requestId)
      if (executionRef.current !== myExecution) return
      setData(compared)
    } catch (e) {
      if (executionRef.current !== myExecution) return
      if (e instanceof ApiError && e.code === "NO_CANDIDATE") {
        setNoCandidate(true)
      } else {
        setError(e instanceof Error ? e.message : "불러오기 실패")
      }
    } finally {
      if (executionRef.current === myExecution) setLoading(false)
    }
  }, [requestId, token, skipScoring])

  return { data, loading, error, noCandidate, load, token }
}

export function usePreview(tripPlaceId: string | undefined, candidateId: string | undefined) {
  const token = useAccessToken()
  const [data, setData] = useState<ReplacementPreviewResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!tripPlaceId || !candidateId) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchReplacementPreview(token, tripPlaceId, candidateId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "미리보기 실패")
    } finally {
      setLoading(false)
    }
  }, [tripPlaceId, candidateId, token])

  const apply = useCallback(async () => {
    if (!tripPlaceId || !candidateId) throw new Error("필수 값이 없습니다.")
    return applyReplacement(token, tripPlaceId, candidateId)
  }, [tripPlaceId, candidateId, token])

  return { data, loading, error, load, apply, token }
}

export function useRemaining(tripId: string | undefined) {
  const token = useAccessToken()
  const [data, setData] = useState<RemainingCongestedResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!tripId) return
    setLoading(true)
    setError(null)
    try {
      setData(await fetchRemainingCongested(token, tripId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "조회 실패")
    } finally {
      setLoading(false)
    }
  }, [tripId, token])

  return { data, loading, error, load, token }
}

export function useConfirmGuide(tripId: string | undefined) {
  const token = useAccessToken()
  const [guide, setGuide] = useState<GuideResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const doConfirm = useCallback(async () => {
    if (!tripId) throw new Error("tripId 없음")
    return confirmTrip(token, tripId)
  }, [tripId, token])

  const loadGuide = useCallback(async () => {
    if (!tripId) return
    setLoading(true)
    setError(null)
    try {
      setGuide(await fetchTripGuide(token, tripId))
    } catch (e) {
      setError(e instanceof Error ? e.message : "가이드 조회 실패")
    } finally {
      setLoading(false)
    }
  }, [tripId, token])

  const share = useCallback(
    async (visibility?: "link" | "private" | "public") => {
      if (!tripId) throw new Error("tripId 없음")
      const res = await createShareLink(token, tripId, visibility)
      if (visibility) {
        setGuide((current) => (current ? { ...current, visibility } : current))
      }
      return res
    },
    [tripId, token],
  )

  const loadPublic = useCallback(async (shareToken: string) => {
    setLoading(true)
    setError(null)
    try {
      setGuide(await fetchPublicGuide(shareToken))
    } catch (e) {
      setError(e instanceof Error ? e.message : "공유 가이드 조회 실패")
    } finally {
      setLoading(false)
    }
  }, [])

  return { guide, loading, error, doConfirm, loadGuide, share, loadPublic, token }
}
