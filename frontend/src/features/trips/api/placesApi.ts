/** 여행 장소(TripPlace) 도메인 API 호출 함수. */
import { apiClient } from "@/api/apiClient"
import type {
  CustomPlaceAddRequest,
  CustomPlaceAddResponse,
  PlaceSearchItem,
  TripPlaceAddResponse,
  TripPlaceOrderItem,
  TripPlaceVisitUpdateRequest,
} from "@/features/trips/types"

export function searchPlaces(keyword: string, regionId?: number) {
  return apiClient
    .get<{ places: PlaceSearchItem[] }>("/places/search", { keyword, regionId })
    .then((res) => res.places)
}

export function addPlaceToTrip(tripId: string, placeId: string, visitTime?: string | null) {
  return apiClient.post<TripPlaceAddResponse>(`/trips/${tripId}/places`, { placeId, visitTime })
}

export function addCustomPlaceToTrip(tripId: string, payload: CustomPlaceAddRequest) {
  return apiClient.post<CustomPlaceAddResponse>(`/trips/${tripId}/places/custom`, payload)
}

export function removeTripPlace(tripPlaceId: string) {
  return apiClient.delete(`/trip-places/${tripPlaceId}`)
}

export function reorderTripPlaces(tripId: string, order: TripPlaceOrderItem[]) {
  return apiClient.patch<{ tripId: string; needsReanalysis: boolean; updatedAt: string }>(
    `/trips/${tripId}/places/order`,
    { order },
  )
}

export function updateTripPlaceVisit(tripPlaceId: string, payload: TripPlaceVisitUpdateRequest) {
  return apiClient.patch(`/trip-places/${tripPlaceId}`, payload)
}
