/** 방문 목적(TripPlacePurpose) 도메인 API 호출 함수. */
import { apiClient } from "@/api/apiClient"
import type { PurposeGetResponse, PurposePutResponse } from "@/features/trips/types"

export function getTripPlacePurpose(tripPlaceId: string) {
  return apiClient.get<PurposeGetResponse>(`/trip-places/${tripPlaceId}/purpose`)
}

export function putTripPlacePurpose(tripPlaceId: string, purposeTagIds: number[]) {
  return apiClient.put<PurposePutResponse>(`/trip-places/${tripPlaceId}/purpose`, { purposeTagIds })
}
