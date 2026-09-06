/** 추천·교체·가이드 API DTO (camelCase) */
export type CongestionLevelApi = "low" | "mid" | "medium" | "high" | "unknown" | "none"

export type RouteScoredCandidate = {
  candidateId: string
  placeId: string
  placeName: string
  experienceScore: number
  routeScore: number
  extraMinutes: number | null
  distancePrevM: number | null
  distanceNextM: number | null
  congestionLevel: CongestionLevelApi
  isRouteEstimated: boolean
  isEligible: boolean
  exclusionReason: string | null
}

export type RouteScoresResponse = {
  requestId: string
  scoredCount: number
  candidates: RouteScoredCandidate[]
}

export type CompareCandidatesResponse = {
  originalPlace: {
    placeId: string
    name: string
    congestionLevel: CongestionLevelApi
  }
  candidates: {
    candidateId: string
    placeName: string
    experienceScore: number
    routeScore: number
    congestionLevel: CongestionLevelApi
    congestionImprovement: string
    extraMinutes: number | null
    distancePrevM: number | null
    distanceNextM: number | null
    reasonText: string | null
    isEligible: boolean
    exclusionReason: string | null
  }[]
  requestId: string
  tripPlaceId: string
}

export type ReplacementPreviewResponse = {
  before: { placeId: string; name: string; congestionLevel: CongestionLevelApi }
  after: { placeId: string; name: string; congestionLevel: CongestionLevelApi }
  extraMinutes: number | null
  totalTravelBefore: number
  totalTravelAfter: number
  candidateId: string
  tripPlaceId: string
}

export type ReplacementResponse = {
  replacementId: string
  tripPlaceId: string
  fromPlaceId: string
  toPlaceId: string
  resolutionStatus: string
  appliedAt: string
}

export type RemainingCongestedResponse = {
  tripId: string
  remainingCount: number
  items: { tripPlaceId: string; placeName: string; level: CongestionLevelApi }[]
  allResolved: boolean
}

export type ConfirmResponse = {
  tripId: string
  status: string
  confirmedAt: string
}

export type GuideResponse = {
  tripId: string
  title: string
  travelDate: string | null
  status: string
  stops: {
    position: number
    placeName: string
    visitTime: string | null
    wasReplaced: boolean
    replacedFrom: string | null
    replaceReason: string | null
    travelToNext: { distanceM: number; durationMin: number } | null
  }[]
  entries: { content: string | null; imageUrl: string | null; displayOrder: number | null }[]
}

export type ShareLinkResponse = {
  token: string
  url: string
  absoluteUrl?: string
  expiresAt: string | null
}

export function toUiCongestion(
  level: CongestionLevelApi | string | null | undefined,
): "high" | "medium" | "low" | "none" {
  if (level === "high") return "high"
  if (level === "mid" || level === "medium") return "medium"
  if (level === "low") return "low"
  return "none"
}
