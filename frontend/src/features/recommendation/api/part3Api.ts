import { API_BASE_URL } from "@/lib/supabase"
import type {
  CompareCandidatesResponse,
  ConfirmResponse,
  GuideResponse,
  RemainingCongestedResponse,
  ReplacementPreviewResponse,
  ReplacementResponse,
  RouteScoresResponse,
  ShareLinkResponse,
} from "../types/part3"

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

export function scoreRoutes(
  accessToken: string,
  requestId: string,
  payload?: {
    tripPlaceId?: string
    transportMode?: string
    extraTimeLimitMinutes?: number
  },
) {
  return v1Fetch<RouteScoresResponse>(
    `${base}/recommendation-requests/${requestId}/route-scores`,
    accessToken,
    { method: "POST", body: JSON.stringify(payload ?? {}) },
  )
}

export function fetchScoredCandidates(accessToken: string, requestId: string) {
  return v1Fetch<CompareCandidatesResponse>(
    `${base}/recommendation-requests/${requestId}/candidates`,
    accessToken,
  )
}

export function fetchReplacementPreview(
  accessToken: string,
  tripPlaceId: string,
  candidateId: string,
) {
  return v1Fetch<ReplacementPreviewResponse>(
    `${base}/trip-places/${tripPlaceId}/replacement-preview`,
    accessToken,
    { method: "POST", body: JSON.stringify({ candidateId }) },
  )
}

export function applyReplacement(
  accessToken: string,
  tripPlaceId: string,
  candidateId: string,
) {
  return v1Fetch<ReplacementResponse>(`${base}/replacements`, accessToken, {
    method: "POST",
    body: JSON.stringify({ tripPlaceId, candidateId }),
  })
}

export function revertReplacement(accessToken: string, replacementId: string) {
  return v1Fetch<{
    replacementId: string
    tripPlaceId: string
    resolutionStatus: string
    revertedAt: string
  }>(`${base}/replacements/${replacementId}/revert`, accessToken, { method: "POST" })
}

export function fetchRemainingCongested(accessToken: string, tripId: string) {
  return v1Fetch<RemainingCongestedResponse>(
    `${base}/trips/${tripId}/remaining-congested`,
    accessToken,
  )
}

export function confirmTrip(accessToken: string, tripId: string) {
  return v1Fetch<ConfirmResponse>(`${base}/trips/${tripId}/confirm`, accessToken, {
    method: "POST",
  })
}

export function fetchTripGuide(accessToken: string, tripId: string) {
  return v1Fetch<GuideResponse>(`${base}/trips/${tripId}/guide`, accessToken)
}

export function createShareLink(
  accessToken: string,
  tripId: string,
  visibility: string = "link",
) {
  return v1Fetch<ShareLinkResponse>(`${base}/trips/${tripId}/share-link`, accessToken, {
    method: "POST",
    body: JSON.stringify({ visibility }),
  })
}

export function fetchPublicGuide(token: string) {
  return v1Fetch<GuideResponse>(`${base}/guide/${token}`, null)
}
