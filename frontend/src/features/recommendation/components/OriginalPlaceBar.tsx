import { Button } from "@/components/common/primitives"
import type { CongestionLevel } from "@/components/common/primitives"
import { congestionTextClass, shortCongestionLabel } from "../utils/compareFormat"

export function OriginalPlaceBar({
  name,
  level,
  keeping = false,
  onKeep,
}: {
  name: string
  level: CongestionLevel
  keeping?: boolean
  onKeep?: () => void
}) {
  const congested = level === "high"
  return (
    <div className="flex w-full items-center justify-between rounded-[var(--radius-field)] bg-surface-sunken px-3.5 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <span className="size-10 shrink-0 rounded-[8px] bg-line-chip" />
        <div className="min-w-0">
          <p className="text-[10px] font-bold tracking-[0.6px] text-ink-faint">원래 장소</p>
          <p className="truncate text-[13px] font-bold leading-[19.5px] text-ink">
            {name}
            <span className="text-ink"> · </span>
            <span className={congested ? "text-congestion-high" : congestionTextClass(level)}>
              {shortCongestionLabel(level)}
            </span>
          </p>
        </div>
      </div>
      <Button
        variant="ghost"
        onClick={onKeep}
        disabled={keeping}
        className="h-[54px] w-auto shrink-0 px-4 text-[15px] font-bold"
      >
        {keeping ? "저장 중…" : "유지"}
      </Button>
    </div>
  )
}
