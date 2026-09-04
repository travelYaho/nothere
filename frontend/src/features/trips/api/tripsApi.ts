/** 여행(Trip) 도메인 API 호출 함수. */
import { apiClient } from "@/api/apiClient"
import type {
  ExperienceTag,
  Region,
  TripConditionsUpdateRequest,
  TripCreateRequest,
  TripCreateResponse,
  TripDetailResponse,
} from "@/features/trips/types"

export function listRegions() {
  return apiClient.get<{ regions: Region[] }>("/regions").then((res) => res.regions)
}

export function listExperienceTags() {
  return apiClient
    .get<{ experienceTags: ExperienceTag[] }>("/experience-tags")
    .then((res) => res.experienceTags)
}

export function createTrip(payload: TripCreateRequest) {
  return apiClient.post<TripCreateResponse>("/trips", payload)
}

export function getTripDetail(tripId: string) {
  return apiClient.get<TripDetailResponse>(`/trips/${tripId}`)
}

export function updateTripConditions(tripId: string, payload: TripConditionsUpdateRequest) {
  return apiClient.patch<{ tripId: string; needsReanalysis: boolean; warnings: string[]; updatedAt: string }>(
    `/trips/${tripId}/conditions`,
    payload,
  )
}
