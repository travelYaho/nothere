/** 로그인 사용자 프로필/통계 도메인 API 호출 함수. */
import { apiClient } from "@/api/apiClient"
import type { UserResponse } from "@/features/auth/types"
import type { UserStatsResponse } from "@/features/users/types"

export function getMe() {
  return apiClient.get<UserResponse>("/users/me")
}

export function getMyStats() {
  return apiClient.get<UserStatsResponse>("/users/me/stats")
}

export function deleteMe() {
  return apiClient.delete("/users/me")
}

export function updateNickname(nickname: string) {
  return apiClient.patch<UserResponse>("/users/me", { nickname })
}
