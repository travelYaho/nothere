import { useCallback, useState } from "react"
import { useSession } from "@/store/sessionStore"
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

/** 로그인 세션(Supabase)의 access token. 로그인 전이면 빈 문자열(백엔드 401). */
export function useAccessToken(): string {
  const { session } = useSession()
  return session?.access_token ?? ""
}

export function useCompareFlow(requestId: string | undefined) {
  const token = useAccessToken()
  const [data, setData] = useState<CompareCandidatesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!requestId) return
    setLoading(true)
    setError(null)
    try {
      await scoreRoutes(token, requestId)
      const compared = await fetchScoredCandidates(token, requestId)
      setData(compared)
    } catch (e) {
      setError(e instanceof Error ? e.message : "불러오기 실패")
    } finally {
      setLoading(false)
    }
  }, [requestId, token])

  return { data, loading, error, load, token }
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

  const share = useCallback(async () => {
    if (!tripId) throw new Error("tripId 없음")
    return createShareLink(token, tripId)
  }, [tripId, token])

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
