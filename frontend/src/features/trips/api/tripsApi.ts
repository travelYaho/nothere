/** 여행(Trip) 도메인 API 호출 함수. */
import { apiClient } from "@/api/apiClient"
import type {
  ExperienceTag,
  HomeResponse,
  Region,
  TripConditionsUpdateRequest,
  TripCreateRequest,
  TripCreateResponse,
  TripDetailResponse,
  TripListResponse,
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

export function deleteTrip(tripId: string) {
  return apiClient.delete(`/trips/${tripId}`)
}

export function listTrips(params: { status?: "draft" | "confirmed"; page?: number } = {}) {
  return apiClient.get<TripListResponse>("/trips", {
    status: params.status,
    page: params.page ?? 1,
  })
}

export function getHomeSummary() {
  return apiClient.get<HomeResponse>("/home")
}
