/** backend/app/schemas/guide.py 와 짝을 이루는 타입들. */
export type GuideSort = "popular" | "recent"

export interface GuideCard {
  tripId: string
  /** 공유 링크가 있을 때만 값이 있다 — "내가 만든" 목록은 공유 안 한 트립도 포함해서 null 일 수 있다. */
  token: string | null
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
