/**
 * GuideFilterSheet — 가이드북 둘러보기 지역/태그 필터 바텀시트.
 * Figma: 여기말GO / node 100:2101 "가이드북 둘러보기" 의 "필터" 버튼에서 진입.
 */
import { BottomSheet } from "@/components/feedback/modals"
import { Button, Chip } from "@/components/common/primitives"
import type { FilterOption } from "@/features/guides/types"

export function GuideFilterSheet({
  open,
  regions,
  tags,
  selectedRegionId,
  selectedTagIds,
  onSelectRegion,
  onToggleTag,
  onReset,
  onApply,
  onClose,
}: {
  open: boolean
  regions: FilterOption[]
  tags: FilterOption[]
  selectedRegionId: number | null
  selectedTagIds: number[]
  onSelectRegion: (id: number | null) => void
  onToggleTag: (id: number) => void
  onReset: () => void
  onApply: () => void
  onClose: () => void
}) {
  return (
    <BottomSheet
      open={open}
      title="필터"
      onClose={onClose}
      footer={
        <div className="flex gap-2.5">
          <Button variant="ghost" className="w-[92px] shrink-0" onClick={onReset}>
            초기화
          </Button>
          <Button block onClick={onApply}>
            적용하기
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-4 pb-2">
        <div>
          <h3 className="pb-2 text-[13px] font-bold text-ink-soft">지역</h3>
          <div className="flex flex-wrap gap-2">
            <Chip
              label="전체"
              selected={selectedRegionId === null}
              onClick={() => onSelectRegion(null)}
            />
            {regions.map((region) => (
              <Chip
                key={region.id}
                label={region.name}
                selected={selectedRegionId === region.id}
                onClick={() => onSelectRegion(region.id)}
              />
            ))}
          </div>
        </div>
        <div>
          <h3 className="pb-2 text-[13px] font-bold text-ink-soft">태그</h3>
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <Chip
                key={tag.id}
                label={tag.name}
                variant="multi"
                selected={selectedTagIds.includes(tag.id)}
                onClick={() => onToggleTag(tag.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </BottomSheet>
  )
}
