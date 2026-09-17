/**
 * GuideLikedView — "좋아요한 가이드북" 화면.
 * Figma: 여기말GO / node 100:2274 "좋아요한 가이드북"
 */
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { GuidebookCard } from "@/components/common/cards"
import { Button } from "@/components/common/primitives"
import { BasicHeader } from "@/components/layout/navigation"
import { exploreGuides, unlikeGuide } from "@/features/guides/api/guidesApi"
import type { GuideCard } from "@/features/guides/types"
import { ApiError } from "@/types/api"

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  return "좋아요한 가이드북을 불러오지 못했습니다."
}

export function GuideLikedView() {
  const navigate = useNavigate()

  const [guides, setGuides] = useState<GuideCard[]>([])
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [likeError, setLikeError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    exploreGuides({ liked: true, page: 1 })
      .then((res) => {
        if (cancelled) return
        setGuides(res.guides)
        setTotalCount(res.totalCount)
        setHasNext(res.hasNext)
        setPage(1)
      })
      .catch((err) => {
        if (!cancelled) setLoadError(toErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleUnlike(guide: GuideCard) {
    // 이 화면은 "좋아요한 것만" 모아보는 목록이라, 취소하면 카드 자체가 빠진다.
    // (공개 갤러리에서 좋아요한 것만 오는 목록이라 token 은 항상 있다.)
    if (!guide.token) return
    const previous = guides
    setGuides((prev) => prev.filter((g) => g.tripId !== guide.tripId))
    setTotalCount((c) => Math.max(0, c - 1))
    try {
      await unlikeGuide(guide.token)
    } catch (err) {
      setGuides(previous)
      setTotalCount((c) => c + 1)
      setLikeError(err instanceof ApiError ? err.message : "좋아요 취소에 실패했습니다.")
    }
  }

  async function loadMore() {
    setLoadingMore(true)
    try {
      const res = await exploreGuides({ liked: true, page: page + 1 })
      setGuides((prev) => [...prev, ...res.guides])
      setHasNext(res.hasNext)
      setPage((p) => p + 1)
    } catch (err) {
      setLoadError(toErrorMessage(err))
    } finally {
      setLoadingMore(false)
    }
  }

  return (
    <div className="relative flex flex-1 flex-col">
      <BasicHeader title="좋아요한 가이드북" onBack={() => navigate(-1)} />

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <p className="px-0.5 pb-2 pt-1 text-[12px] font-medium text-ink-faint">
          {totalCount}개 저장됨
        </p>

        {likeError && (
          <p className="mb-2 rounded-[var(--radius-field)] bg-congestion-high-bg px-3 py-2 text-[12px] font-medium text-congestion-high">
            {likeError}{" "}
            <button onClick={() => setLikeError(null)} className="underline">
              닫기
            </button>
          </p>
        )}

        {loading && <p className="py-10 text-center text-[13px] text-ink-muted">불러오는 중...</p>}
        {!loading && loadError && (
          <p className="py-10 text-center text-[13px] font-medium text-congestion-high">{loadError}</p>
        )}
        {!loading && !loadError && guides.length === 0 && (
          <p className="py-10 text-center text-[13px] text-ink-muted">아직 좋아요한 가이드북이 없어요.</p>
        )}

        {!loading && !loadError && guides.length > 0 && (
          <div className="flex flex-col gap-2.5">
            {guides.map((guide) => (
              <GuidebookCard
                key={guide.tripId}
                title={guide.title}
                regionName={guide.regionName}
                placeCount={guide.placeCount}
                tags={guide.tags}
                authorNickname={guide.authorNickname}
                coverImageUrl={guide.coverImageUrl}
                likeCount={guide.likeCount}
                isLikedByMe={guide.isLikedByMe}
                onClick={() => navigate(`/guide/${guide.token}`)}
                onToggleLike={() => void handleUnlike(guide)}
              />
            ))}
          </div>
        )}

        {!loading && !loadError && hasNext && (
          <div className="pt-3">
            <Button variant="ghost" block loading={loadingMore} onClick={() => void loadMore()}>
              더보기
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
