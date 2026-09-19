import { ChevronDown } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { toUiCongestion, type CompareCandidate } from "../types/part3"
import {
  candidateLetter,
  congestionTextClass,
  districtFromAddress,
  formatExtraMinutes,
  formatNeighborDistance,
  formatTravelChange,
  reasonLines,
  shortCongestionLabel,
} from "../utils/compareFormat"

function LetterThumb({
  letter,
  size,
}: {
  letter: string
  size: "expanded" | "collapsed"
}) {
  const box = size === "expanded" ? "size-16 rounded-[12px]" : "size-11 rounded-[12px]"
  return (
    <span className={`flex shrink-0 items-center justify-center bg-surface-chip ${box}`}>
      <span className="flex size-5 items-center justify-center rounded-[6px] bg-ink text-[10px] font-bold leading-[15px] text-white">
        {letter}
      </span>
    </span>
  )
}

function MetricCell({
  label,
  value,
  valueClass = "text-ink",
  divided = false,
}: {
  label: string
  value: string
  valueClass?: string
  divided?: boolean
}) {
  return (
    <div className={["flex flex-1 flex-col items-center p-2.5", divided ? "border-l-[0.667px] border-line-soft" : ""].join(" ")}>
      <p className="text-center text-[10px] font-medium leading-[15px] text-ink-faint">{label}</p>
      <p className={`pt-0.5 text-center text-[13px] font-bold leading-[19.5px] ${valueClass}`}>{value}</p>
    </div>
  )
}

export function AlternativeCandidateCard({
  candidate,
  index,
  expanded,
  applying = false,
  onToggle,
  onChange,
  onMap,
  onDetail,
  originalTravelMinutes,
}: {
  candidate: CompareCandidate
  index: number
  expanded: boolean
  applying?: boolean
  originalTravelMinutes?: number | null
  onToggle: () => void
  onChange: () => void
  onMap: () => void
  onDetail?: () => void
}) {
  const letter = candidateLetter(index)
  const level = toUiCongestion(candidate.congestionLevel)
  const extraShort = formatExtraMinutes(candidate.extraMinutes)
  const extra = formatTravelChange(
    originalTravelMinutes,
    candidate.travelMinutes,
    candidate.extraMinutes,
  ) ?? extraShort
  const firstTag = (candidate.tags ?? [])[0]?.name

  if (!expanded) {
    return (
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-3 rounded-[var(--radius-field)] bg-surface p-3.5 text-left"
      >
        <LetterThumb letter={letter} size="collapsed" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[14px] font-bold leading-[21px] text-ink">
            {candidate.placeName}
          </span>
          <span className="block truncate text-[11px] font-medium leading-[16.5px]">
            <span className={congestionTextClass(level)}>{shortCongestionLabel(level)}</span>
            {extraShort && <span className="text-ink-faint">{` · ${extraShort}`}</span>}
            {firstTag && <span className="text-ink-faint">{` · ${firstTag}`}</span>}
          </span>
        </span>
        <ChevronDown size={16} className="shrink-0 text-ink-faint" />
      </button>
    )
  }

  const district = districtFromAddress(candidate.address)
  const meta = [district].filter(Boolean).join(" · ")
  const lines = reasonLines(candidate)
  const distance = formatNeighborDistance(candidate.distancePrevM, candidate.distanceNextM)
  const tags = candidate.tags ?? []

  return (
    <div className="flex w-full flex-col rounded-[var(--radius-field)] border-[1.333px] border-primary bg-surface p-4">
      <button type="button" onClick={onToggle} className="flex w-full items-start gap-3 text-left">
        <LetterThumb letter={letter} size="expanded" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[15px] font-bold leading-[22.5px] text-ink">
            {candidate.placeName}
          </span>
          {meta && (
            <span className="mt-0.5 block truncate text-[11px] font-medium leading-[16.5px] text-ink-faint">
              {meta}
            </span>
          )}
        </span>
      </button>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-2.5">
          {tags.slice(0, 3).map((tag) => (
            <span
              key={tag.id}
              className="rounded-full bg-surface-sunken px-2.5 py-1 text-[11px] font-semibold leading-[16.5px] text-ink-soft"
            >
              {tag.name}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 overflow-hidden rounded-[12px] bg-canvas">
        <div className="flex">
          <MetricCell
            label="예상 집중도"
            value={shortCongestionLabel(level)}
            valueClass={congestionTextClass(level)}
          />
          <MetricCell
            label="이동 시간 변화"
            value={extra ?? "—"}
            valueClass={extra && extra.length > 10 ? "text-[11px] text-ink" : "text-ink"}
            divided
          />
          <MetricCell label="앞뒤 일정과의 거리" value={distance ?? "—"} divided />
        </div>
      </div>

      {lines.length > 0 && (
        <p className="pt-3 text-[11px] font-normal leading-[17.875px] text-ink-muted">
          {lines.map((line) => (
            <span key={line} className="block">
              {line}
            </span>
          ))}
        </p>
      )}

      <div className="flex items-start gap-2 pt-3">
        <Button
          onClick={onChange}
          disabled={applying}
          className="min-w-0 flex-1 text-[16px]"
        >
          {applying ? "변경 중…" : "이 장소로 변경"}
        </Button>
        <Button
          variant="ghost"
          onClick={onMap}
          className="h-[54px] w-[52px] shrink-0 px-0 text-[15px] font-bold"
        >
          지도
        </Button>
        {onDetail && (
          <Button
            variant="ghost"
            onClick={onDetail}
            className="h-[54px] w-[52px] shrink-0 px-0 text-[15px] font-bold"
          >
            상세
          </Button>
        )}
      </div>
    </div>
  )
}
