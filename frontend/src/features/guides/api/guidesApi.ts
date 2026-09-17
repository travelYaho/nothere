/** 가이드북 공개 갤러리/좋아요 도메인 API 호출 함수. */
import { apiClient } from "@/api/apiClient"
import type {
  ExploreResponse,
  FiltersResponse,
  GuideSort,
  LikeToggleResponse,
} from "@/features/guides/types"

export interface ExploreGuidesParams {
  sort?: GuideSort
  regionId?: number | null
  tagIds?: number[]
  page?: number
  liked?: boolean
}

export function exploreGuides(params: ExploreGuidesParams = {}) {
  return apiClient.get<ExploreResponse>("/guides/explore", {
    sort: params.sort ?? "popular",
    regionId: params.regionId ?? undefined,
    tagIds: params.tagIds?.length ? params.tagIds.join(",") : undefined,
    page: params.page ?? 1,
    liked: params.liked || undefined,
  })
}

export function listMyGuides(page = 1) {
  return apiClient.get<ExploreResponse>("/guides/mine", { page })
}

export function getGuideFilters() {
  return apiClient.get<FiltersResponse>("/guides/filters")
}

export function likeGuide(token: string) {
  return apiClient.post<LikeToggleResponse>(`/guides/${token}/like`)
}

export function unlikeGuide(token: string) {
  return apiClient.delete<LikeToggleResponse>(`/guides/${token}/like`)
}
