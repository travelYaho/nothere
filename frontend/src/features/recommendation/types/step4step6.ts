/** STEP4(집중도 분석) / STEP5·6(방문 목적 선택 + 대안 후보 탐색) DTO */
import type { CongestionLevelApi } from "./part3"

export type AnalysisItem = {
  tripPlaceId: string
  placeId: string
  placeName: string
  analysisStatus: "success" | "unavailable" | "failed"
  level: CongestionLevelApi | null
  unknownReason: string | null
  ruleVersion: string | null
  isFixed: boolean
  resolutionStatus: string
  canRecommendAlternative: boolean
  analyzedAt: string | null
}

export type AnalysisResponse = {
  tripId: string
  highConcentrationCount: number
  items: AnalysisItem[]
}

export type ExperienceTag = {
  id: number
  code: string
  name: string
}

export type CreateRecommendationRequestResponse = {
  requestId: string
  tripPlaceId: string
  searchMode: string
  status: "success" | "no_candidate"
  candidateCount: number
  excludedCount: number
}
