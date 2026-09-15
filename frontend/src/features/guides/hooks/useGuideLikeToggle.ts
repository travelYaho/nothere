/** 가이드북 카드 목록에서 좋아요를 낙관적으로 토글하는 공용 훅. */
import { useState, type Dispatch, type SetStateAction } from "react"
import { likeGuide, unlikeGuide } from "@/features/guides/api/guidesApi"
import type { GuideCard } from "@/features/guides/types"
import { ApiError } from "@/types/api"

export function useGuideLikeToggle(setGuides: Dispatch<SetStateAction<GuideCard[]>>) {
  const [likeError, setLikeError] = useState<string | null>(null)

  async function toggleLike(guide: GuideCard) {
    if (!guide.token) return // 공유 안 한 트립("내가 만든" 목록)엔 좋아요 자체가 없다.
    const token = guide.token
    const wasLiked = guide.isLikedByMe
    const wasCount = guide.likeCount
    setGuides((prev) =>
      prev.map((g) =>
        g.tripId === guide.tripId
          ? { ...g, isLikedByMe: !wasLiked, likeCount: wasCount + (wasLiked ? -1 : 1) }
          : g,
      ),
    )
    try {
      const res = wasLiked ? await unlikeGuide(token) : await likeGuide(token)
      setGuides((prev) =>
        prev.map((g) =>
          g.tripId === guide.tripId
            ? { ...g, isLikedByMe: res.isLikedByMe, likeCount: res.likeCount }
            : g,
        ),
      )
    } catch (err) {
      setGuides((prev) =>
        prev.map((g) =>
          g.tripId === guide.tripId ? { ...g, isLikedByMe: wasLiked, likeCount: wasCount } : g,
        ),
      )
      setLikeError(err instanceof ApiError ? err.message : "좋아요 처리에 실패했습니다.")
    }
  }

  return { toggleLike, likeError, clearLikeError: () => setLikeError(null) }
}
