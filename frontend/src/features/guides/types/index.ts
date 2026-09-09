/** backend/app/schemas/guide.py 와 짝을 이루는 타입들. */
export type GuideSort = "popular" | "recent"

export interface GuideCard {
  token: string
  title: string
  regionName: string
  placeCount: number
  tags: string[]
  authorNickname: string
  coverImageUrl: string | null
  likeCount: number
  isLikedByMe: boolean
}

export interface ExploreResponse {
  guides: GuideCard[]
  page: number
  hasNext: boolean
  totalCount: number
}

export interface FilterOption {
  id: number
  name: string
}

export interface FiltersResponse {
  regions: FilterOption[]
  tags: FilterOption[]
}

export interface LikeToggleResponse {
  token: string
  likeCount: number
  isLikedByMe: boolean
}
