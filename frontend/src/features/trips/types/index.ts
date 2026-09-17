/** backend/app/schemas/region.py, experience_tag.py, trip.py 와 짝을 이루는 타입들. */
export interface Region {
  id: number
  name: string
}

export interface ExperienceTag {
  id: number
  name: string
}

export type CompanionType = "solo" | "couple" | "friends" | "family"

export interface TripCreateRequest {
  title?: string | null
  travelDate: string // YYYY-MM-DD
  regionId: number
  companionType?: string | null
  transportMode?: string | null
  extraTimeLimitMinutes?: number | null
  preferredExperienceTagIds: number[]
}

export interface TripCreateResponse {
  tripId: string
  title: string
  status: string
  currentStep: number
  createdAt: string
}

export interface TripPlaceDetail {
  tripPlaceId: string
  placeId: string
  name: string
  visitOrder: number
  visitTime: string | null
  durationMinutes: number | null
  isFixed: boolean
}

export interface TripDetailResponse {
  tripId: string
  title: string
  travelDate: string | null
  regionId: number
  regionName: string
  companionType: string | null
  transportMode: string | null
  extraTimeLimitMinutes: number | null
  status: string
  currentStep: number
  needsReanalysis: boolean
  preferredExperienceTagIds: number[]
  places: TripPlaceDetail[]
}

export interface PlaceSearchItem {
  placeId: string
  name: string
  address: string | null
  latitude: number | null
  longitude: number | null
}

export interface TripPlaceAddResponse {
  tripPlaceId: string
  tripId: string
  placeId: string
  visitOrder: number
  visitTime: string | null
  isFixed: boolean
}

export interface CustomPlaceAddRequest {
  name: string
  address: string
  visitTime?: string | null
}

export interface CustomPlaceAddResponse extends TripPlaceAddResponse {
  name: string
}

export interface TripPlaceOrderItem {
  tripPlaceId: string
  visitOrder: number
}

export interface TripPlaceVisitUpdateRequest {
  visitTime?: string | null
  durationMinutes?: number | null
  isFixed?: boolean | null
}

export interface PurposeTag {
  id: number
  name: string
}

export interface PurposeGetResponse {
  tripPlaceId: string
  purposeTags: PurposeTag[]
}

export interface PurposePutResponse {
  tripPlaceId: string
  purposeTags: PurposeTag[]
  updatedAt: string
}

export interface TripConditionsUpdateRequest {
  title?: string | null
  travelDate?: string
  regionId?: number
  companionType?: string | null
  transportMode?: string | null
  extraTimeLimitMinutes?: number | null
  preferredExperienceTagIds?: number[]
}

/** 카드를 누르면 resumeUrl 로 이동한다 — 확정된 일정이면 가이드북, 아니면 STEP3 장소 목록. */
export interface TripSummary {
  tripId: string
  title: string
  travelDate: string | null
  regionName: string
  placeCount: number
  status: string
  resumeUrl: string
}

export interface TripListResponse {
  trips: TripSummary[]
  page: number
  hasNext: boolean
  totalCount: number
}

/** backend/app/schemas/home.py 와 짝을 이루는 타입들. */
export interface ScheduleSummary {
  scheduleId: string
  title: string
  travelDate: string | null
  regionName: string
  placeCount: number
  status: string
  resumeUrl: string
}

export interface HomeUser {
  id: string
  nickname: string
  profileImageUrl: string | null
}

export interface HomeResponse {
  user: HomeUser
  draftSchedule: ScheduleSummary | null
  recentSchedules: ScheduleSummary[]
}
