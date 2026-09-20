import { API_BASE_URL } from "@/lib/apiBaseUrl"
import { updateTripPlaceVisit } from "@/features/trips/api/placesApi"
import type {
  AnalysisResponse,
  CreateRecommendationRequestResponse,
  ExperienceTag,
} from "../types/step4step6"

type Envelope<T> = { data: T; meta?: Record<string, unknown> }

function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>
    const err = b.error as Record<string, unknown> | undefined
    if (err?.message && typeof err.message === "string") return err.message
    if (typeof b.message === "string") return b.message
  }
  return `요청 실패 (${status})`
}

async function v1Fetch<T>(
  path: string,
  accessToken: string | null,
  init?: RequestInit,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(errorMessage(body, response.status))
  }
  if (body && typeof body === "object" && "data" in body) {
    return (body as Envelope<T>).data
  }
  return body as T
}

const base = "/api"

export function runAnalysis(accessToken: string, tripId: string) {
  return v1Fetch<AnalysisResponse>(`${base}/trips/${tripId}/analysis`, accessToken, {
    method: "POST",
  })
}

export function fetchAnalysis(accessToken: string, tripId: string, status?: "CROWDED") {
  const query = status ? `?status=${status}` : ""
  return v1Fetch<AnalysisResponse>(`${base}/trips/${tripId}/analysis${query}`, accessToken)
}

export function fetchExperienceTags() {
  return v1Fetch<{ experienceTags: ExperienceTag[] }>(`${base}/experience-tags`, null).then(
    (res) => res.experienceTags,
  )
}

/** "유지" — 이 장소를 고정해 대안 탐색/재분석 대상에서 제외한다. */
export function keepTripPlace(tripPlaceId: string) {
  return updateTripPlaceVisit(tripPlaceId, { isFixed: true })
}

export function createRecommendationRequest(
  accessToken: string,
  tripPlaceId: string,
  payload: { purposeTagIds?: number[]; searchMode?: string },
) {
  return v1Fetch<CreateRecommendationRequestResponse>(
    `${base}/trip-places/${tripPlaceId}/recommendation-requests`,
    accessToken,
    { method: "POST", body: JSON.stringify(payload) },
  )
}
