import { useCallback, useEffect, useState } from "react"
import {
  createRecommendationRequest,
  fetchExperienceTags,
  runAnalysis,
} from "../api/step4step6Api"
import type { AnalysisResponse, CreateRecommendationRequestResponse, ExperienceTag } from "../types/step4step6"
import { useAccessToken } from "./usePart3"

export function useRunAnalysis(tripId: string | undefined) {
  const token = useAccessToken()
  const [data, setData] = useState<AnalysisResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async (): Promise<AnalysisResponse | null> => {
    if (!tripId) return null
    setLoading(true)
    setError(null)
    try {
      const result = await runAnalysis(token, tripId)
      setData(result)
      return result
    } catch (e) {
      setError(e instanceof Error ? e.message : "분석 실패")
      return null
    } finally {
      setLoading(false)
    }
  }, [tripId, token])

  return { data, loading, error, run }
}

export function useExperienceTags() {
  const [tags, setTags] = useState<ExperienceTag[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchExperienceTags()
      .then((result) => {
        if (!cancelled) setTags(result)
      })
      .catch(() => {
        if (!cancelled) setTags([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { tags, loading }
}

export function useCreateRecommendationRequest(tripPlaceId: string | undefined) {
  const token = useAccessToken()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const create = useCallback(
    async (purposeTagIds: number[], searchMode?: string): Promise<CreateRecommendationRequestResponse> => {
      if (!tripPlaceId) throw new Error("tripPlaceId 없음")
      setLoading(true)
      setError(null)
      try {
        return await createRecommendationRequest(token, tripPlaceId, {
          purposeTagIds,
          searchMode,
        })
      } catch (e) {
        const message = e instanceof Error ? e.message : "대안 후보 탐색 실패"
        setError(message)
        throw e
      } finally {
        setLoading(false)
      }
    },
    [tripPlaceId, token],
  )

  return { create, loading, error }
}
