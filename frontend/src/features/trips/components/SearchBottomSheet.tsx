/**
 * SearchBottomSheet — STEP3 장소 검색 바텀시트.
 * Figma: 여기말GO / node 48:3158 "검색 바텀 시트" (분류/예상 대기시간 칩은
 * 제외했다 — 둘 다 place/place_experience_tag 처럼 장소별 공용 테이블에
 * 저장되는 값이라, TourAPI 장소는 검색 결과가 여러 사용자/일정에 걸쳐
 * 재사용(dedup)돼서 그대로 넣으면 값이 서로 덮어써지거나 중복키로
 * 터진다 — 팀 확인 후 안전한 저장 위치가 정해지면 추가하기로 함)
 */
import { useState } from "react"
import { Close, Search } from "@/components/common/icons"
import type { PlaceSearchItem } from "@/features/trips/types"

export function SearchBottomSheet({
  keyword,
  onKeywordChange,
  onClose,
  results,
  searching,
  searchError,
  addedPlaceIds,
  pendingPlaceId,
  onAdd,
  onAddCustom,
}: {
  keyword: string
  onKeywordChange: (value: string) => void
  onClose: () => void
  results: PlaceSearchItem[]
  searching: boolean
  searchError: string | null
  addedPlaceIds: Set<string>
  pendingPlaceId: string | null
  onAdd: (placeId: string, visitTime: string | null) => void
  onAddCustom: () => void
}) {
  const [expandedPlaceId, setExpandedPlaceId] = useState<string | null>(null)
  const [visitTime, setVisitTime] = useState("")
  return (
    <div className="absolute inset-0 z-30 flex flex-col justify-end">
      <div className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <div className="animate-sheet-up relative flex max-h-[80%] flex-col rounded-t-[var(--radius-banner)] bg-canvas shadow-[var(--shadow-sheet)]">
        <div className="flex justify-center pt-2.5">
          <span className="h-1 w-10 rounded-full bg-line-chip" />
        </div>

        <div className="flex items-center gap-3 px-4 py-3">
          <div className="flex h-[46px] flex-1 items-center gap-2.5 rounded-[var(--radius-field)] border-[0.667px] border-primary bg-surface px-4">
            <Search size={18} className="shrink-0 text-ink-faint" />
            <input
              autoFocus
              value={keyword}
              onChange={(e) => onKeywordChange(e.target.value)}
              placeholder="관광지 검색"
              className="w-full bg-transparent text-[14px] text-ink outline-none placeholder:text-ink-ghost"
            />
            {keyword && (
              <button onClick={() => onKeywordChange("")} className="shrink-0 text-ink-faint">
                <Close size={12} />
              </button>
            )}
          </div>
          <button onClick={onClose} className="shrink-0 text-[14px] font-bold text-ink-soft">
            취소
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-2">
          {searchError && (
            <p className="py-4 text-center text-[13px] font-medium text-congestion-high">{searchError}</p>
          )}
          {!searchError && searching && (
            <p className="py-4 text-center text-[13px] text-ink-muted">검색 중...</p>
          )}
          {!searchError && !searching && keyword.trim() && results.length === 0 && (
            <p className="py-4 text-center text-[13px] text-ink-muted">검색 결과가 없어요.</p>
          )}
          {!searching &&
            results.map((place) => {
              const isAdded = addedPlaceIds.has(place.placeId)
              const isPending = pendingPlaceId === place.placeId
              const isExpanded = expandedPlaceId === place.placeId
              return (
                <div key={place.placeId} className="border-b-[0.667px] border-line-soft py-3">
                  <div className="flex items-center gap-3">
                    <div className="size-12 shrink-0 rounded-[12px] bg-surface-chip" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[14px] font-bold text-ink">{place.name}</p>
                      <p className="truncate text-[11px] font-medium text-ink-faint">
                        {[place.category, place.address].filter(Boolean).join(" · ")}
                      </p>
                    </div>
                    <button
                      disabled={isAdded || isPending}
                      onClick={() => {
                        if (isAdded || isPending) return
                        if (isExpanded) {
                          onAdd(place.placeId, visitTime || null)
                          setExpandedPlaceId(null)
                          setVisitTime("")
                        } else {
                          setExpandedPlaceId(place.placeId)
                          setVisitTime("")
                        }
                      }}
                      className={[
                        "shrink-0 rounded-full px-3.5 py-2 text-[12px] font-bold",
                        isAdded
                          ? "bg-surface-sunken text-ink-ghost"
                          : "bg-primary text-primary-foreground",
                        isPending ? "opacity-60" : "",
                      ].join(" ")}
                    >
                      {isAdded ? "추가됨" : isPending ? "추가 중" : isExpanded ? "확인" : "추가"}
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="pb-1 pl-[60px] pt-2.5">
                      <label className="block pb-1.5 text-[13px] font-semibold text-ink-soft">
                        방문 예정 시간
                      </label>
                      <input
                        type="time"
                        value={visitTime}
                        onChange={(e) => setVisitTime(e.target.value)}
                        className="h-[46px] w-[160px] rounded-[var(--radius-field)] border-[0.667px] border-line bg-surface px-3.5 text-[14px] text-ink outline-none"
                      />
                    </div>
                  )}
                </div>
              )
            })}
        </div>

        <button
          onClick={onAddCustom}
          className="flex flex-col items-center pb-5 pt-2 text-[14px] font-medium text-ink-faint"
        >
          장소 직접 추가
        </button>
      </div>
    </div>
  )
}
