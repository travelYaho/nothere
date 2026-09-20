import { circledIndex } from "./utils"
import { formatVisitTime } from "@/features/trips/utils/placeOrder"
import type { GuideStop } from "@/features/recommendation/types/part3"

export function GuideScheduleItem({
  stop,
  index,
  showConnector,
}: {
  stop: GuideStop
  index: number
  showConnector: boolean
}) {
  return (
    <div className="relative flex items-center gap-3 py-3.5">
      {showConnector && (
        <span
          aria-hidden
          className="absolute left-[13px] top-[46px] h-[calc(100%-18px)] w-0.5 rounded-full bg-[#c8d7cd]"
        />
      )}
      <div className="relative z-[1] flex size-7 shrink-0 items-center justify-center rounded-[14px] bg-[#1f8a56] text-[11px] font-extrabold text-white">
        {circledIndex(index)}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[12px] font-semibold text-[#1f8a56]">
          {formatVisitTime(stop.visitTime) || "--:--"}
        </p>
        <p className="truncate text-[14px] font-bold leading-5 text-ink">{stop.placeName}</p>
      </div>
      {stop.imageUrl ? (
        <div className="size-14 shrink-0 overflow-hidden rounded-[10px] bg-surface-sunken">
          <img src={stop.imageUrl} alt="" className="size-full object-cover" />
        </div>
      ) : null}
    </div>
  )
}
