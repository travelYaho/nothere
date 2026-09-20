import { API_BASE_URL } from "@/lib/supabase"
import { ApiError } from "@/types/api"
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
    // { error: { code, message } } 형태면 code를 보존한 ApiError로 던진다 — 화면이
    // 에러 문구(바뀔 수 있음)가 아니라 code로 분기할 수 있게 한다(2026-09-18, 코드
    // 리뷰로 발견 — "요청 미완료"와 "후보 없음"이 같은 문구를 썼던 문제).
    const err = body && typeof body === "object" ? (body as { error?: unknown }).error : undefined
    if (
      err &&
      typeof err === "object" &&
      typeof (err as { code?: unknown }).code === "string" &&
      typeof (err as { message?: unknown }).message === "string"
    ) {
      throw new ApiError(response.status, err as { code: string; message: string })
    }
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
  visibility?: "link" | "private" | "public",
) {
  return v1Fetch<ShareLinkResponse>(`${base}/trips/${tripId}/share-link`, accessToken, {
    method: "POST",
    body: JSON.stringify(visibility ? { visibility } : {}),
  })
}

export function fetchPublicGuide(token: string) {
  return v1Fetch<GuideResponse>(`${base}/guide/${token}`, null)
}

export function saveGuideMemo(accessToken: string, tripId: string, content: string) {
  return v1Fetch<{ memo: string | null }>(`${base}/trips/${tripId}/guide/memo`, accessToken, {
    method: "PATCH",
    body: JSON.stringify({ content }),
  })
}
