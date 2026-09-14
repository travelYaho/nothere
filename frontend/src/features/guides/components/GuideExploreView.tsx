/**
 * GuideExploreView — "가이드북 둘러보기" 공개 갤러리 화면.
 * Figma: 여기말GO / node 100:2101 "가이드북 둘러보기 (정렬·필터·페이지)"
 */
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ChevronLeft, ChevronRight, Sliders } from "@/components/common/icons"
import { GuidebookCard } from "@/components/common/cards"
import { BasicHeader } from "@/components/layout/navigation"
import { exploreGuides, getGuideFilters } from "@/features/guides/api/guidesApi"
import { useGuideLikeToggle } from "@/features/guides/hooks/useGuideLikeToggle"
import { GuideFilterSheet } from "@/features/guides/components/GuideFilterSheet"
import type { FiltersResponse, GuideCard, GuideSort } from "@/features/guides/types"
import { ApiError } from "@/types/api"

const PAGE_SIZE = 8

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  return "가이드북을 불러오지 못했습니다."
}

export function GuideExploreView() {
  const navigate = useNavigate()

  const [sort, setSort] = useState<GuideSort>("popular")
  const [regionId, setRegionId] = useState<number | null>(null)
  const [tagIds, setTagIds] = useState<number[]>([])
  const [page, setPage] = useState(1)

  const [guides, setGuides] = useState<GuideCard[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [filters, setFilters] = useState<FiltersResponse>({ regions: [], tags: [] })
  const [filterOpen, setFilterOpen] = useState(false)
  const [draftRegionId, setDraftRegionId] = useState<number | null>(null)
  const [draftTagIds, setDraftTagIds] = useState<number[]>([])

  const { toggleLike, likeError, clearLikeError } = useGuideLikeToggle(setGuides)

  useEffect(() => {
    getGuideFilters()
      .then(setFilters)
      .catch(() => setFilters({ regions: [], tags: [] }))
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    exploreGuides({ sort, regionId, tagIds, page })
      .then((res) => {
        if (cancelled) return
        setGuides(res.guides)
        setTotalCount(res.totalCount)
        setHasNext(res.hasNext)
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
  }, [sort, regionId, tagIds, page])

  function changeSort(next: GuideSort) {
    setSort(next)
    setPage(1)
  }

  function openFilterSheet() {
    setDraftRegionId(regionId)
    setDraftTagIds(tagIds)
    setFilterOpen(true)
  }

  function applyFilters() {
    setRegionId(draftRegionId)
    setTagIds(draftTagIds)
    setPage(1)
    setFilterOpen(false)
  }

  function resetFilters() {
    setDraftRegionId(null)
    setDraftTagIds([])
  }

  function toggleDraftTag(tagId: number) {
    setDraftTagIds((prev) =>
      prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId],
    )
  }

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE))

  return (
    <div className="relative flex flex-1 flex-col">
      <BasicHeader title="가이드북 둘러보기" onBack={() => navigate(-1)} />

      <div className="flex items-center justify-between px-4 pb-2 pt-1">
        <div className="flex gap-1.5">
          {(["popular", "recent"] as const).map((option) => (
            <button
              key={option}
              onClick={() => changeSort(option)}
              className={[
                "rounded-[var(--radius-pill)] px-3.5 py-1.5 text-[12px] font-bold transition-colors",
                sort === option ? "bg-primary text-primary-foreground" : "bg-surface text-ink-soft",
              ].join(" ")}
            >
              {option === "popular" ? "인기순" : "최근순"}
            </button>
          ))}
        </div>
        <button
          onClick={openFilterSheet}
          className="flex items-center gap-1 rounded-[var(--radius-pill)] border-[0.667px] border-line-chip bg-surface px-3 py-1.5 text-[12px] font-bold text-ink-soft"
        >
          <Sliders size={14} />
          필터
          {(regionId !== null || tagIds.length > 0) && (
            <span className="ml-0.5 inline-block h-1.5 w-1.5 rounded-full bg-primary" />
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <p className="px-0.5 pb-2 text-[12px] font-medium text-ink-faint">
          총 {totalCount}개의 가이드북
        </p>

        {likeError && (
          <p className="mb-2 rounded-[var(--radius-field)] bg-congestion-high-bg px-3 py-2 text-[12px] font-medium text-congestion-high">
            {likeError}{" "}
            <button onClick={clearLikeError} className="underline">
              닫기
            </button>
          </p>
        )}

        {loading && <p className="py-10 text-center text-[13px] text-ink-muted">불러오는 중...</p>}
        {!loading && loadError && (
          <p className="py-10 text-center text-[13px] font-medium text-congestion-high">{loadError}</p>
        )}
        {!loading && !loadError && guides.length === 0 && (
          <p className="py-10 text-center text-[13px] text-ink-muted">조건에 맞는 가이드북이 없어요.</p>
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
                onToggleLike={() => void toggleLike(guide)}
              />
            ))}
          </div>
        )}

        {!loading && !loadError && totalPages > 1 && (
          <div className="flex items-center justify-center gap-1.5 pt-4">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-surface text-ink-soft disabled:opacity-30"
            >
              <ChevronLeft size={16} />
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((num) => (
              <button
                key={num}
                onClick={() => setPage(num)}
                className={[
                  "flex h-8 w-8 items-center justify-center rounded-[10px] text-[13px] font-bold",
                  num === page ? "bg-primary text-primary-foreground" : "bg-surface text-ink-soft",
                ].join(" ")}
              >
                {num}
              </button>
            ))}
            <button
              disabled={!hasNext}
              onClick={() => setPage((p) => p + 1)}
              className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-surface text-ink-soft disabled:opacity-30"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>

      <GuideFilterSheet
        open={filterOpen}
        regions={filters.regions}
        tags={filters.tags}
        selectedRegionId={draftRegionId}
        selectedTagIds={draftTagIds}
        onSelectRegion={setDraftRegionId}
        onToggleTag={toggleDraftTag}
        onReset={resetFilters}
        onApply={applyFilters}
        onClose={() => setFilterOpen(false)}
      />
    </div>
  )
}
