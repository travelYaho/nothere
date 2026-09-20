/** 추천·교체·가이드 API DTO (camelCase) */
export type CongestionLevelApi = "low" | "mid" | "medium" | "high" | "unknown" | "none"

export type RouteScoredCandidate = {
  candidateId: string
  placeId: string
  placeName: string
  experienceScore: number
  routeScore: number
  extraMinutes: number | null
  travelMinutes?: number | null
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

export type CompareCandidateTag = {
  id: number
  name: string
}

export type CompareCandidate = {
  candidateId: string
  placeName: string
  experienceScore: number
  routeScore: number
  congestionLevel: CongestionLevelApi
  congestionImprovement: string
  extraMinutes: number | null
  travelMinutes?: number | null
  distancePrevM: number | null
  distanceNextM: number | null
  reasonText: string | null
  isEligible: boolean
  exclusionReason: string | null
  tags?: CompareCandidateTag[]
  address?: string | null
}

export type CompareCandidatesResponse = {
  originalPlace: {
    placeId: string
    name: string
    congestionLevel: CongestionLevelApi
    travelMinutes?: number | null
  }
  candidates: CompareCandidate[]
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

export type GuideStop = {
  position: number
  placeName: string
  visitTime: string | null
  stayMinutes?: number | null
  wasReplaced: boolean
  replacedFrom: string | null
  replaceReason: string | null
  extraMinutes?: number | null
  beforeLevel?: string | null
  afterLevel?: string | null
  travelToNext: { distanceM: number; durationMin: number } | null
  imageUrl?: string | null
}

export type GuideResponse = {
  tripId: string
  title: string
  travelDate: string | null
  regionName?: string | null
  cityName?: string | null
  districtName?: string | null
  totalTravelMin?: number | null
  tags?: string[]
  memo?: string | null
  status: string
  coverImageUrl?: string | null
  stops: GuideStop[]
  entries: { content: string | null; imageUrl: string | null; displayOrder: number | null }[]
  visibility?: "link" | "private" | "public"
  shareToken?: string | null
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
