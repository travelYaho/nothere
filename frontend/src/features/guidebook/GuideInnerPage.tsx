import { useEffect, useRef, useState } from "react"
import { Calendar, Pencil } from "@/components/common/icons"
import type { GuideResponse } from "@/features/recommendation/types/part3"
import { GuideScheduleItem } from "./GuideScheduleItem"
import { innerDatePill } from "./utils"

export function GuideInnerPage({
  guide,
  memoReadOnly,
  onSaveMemo,
}: {
  guide: GuideResponse
  memoReadOnly?: boolean
  onSaveMemo?: (content: string) => Promise<unknown>
}) {
  const [memo, setMemo] = useState(guide.memo ?? "")
  const [saveMsg, setSaveMsg] = useState<string | null>(null)
  const debounceRef = useRef<number | null>(null)
  const lastSaved = useRef(guide.memo ?? "")

  useEffect(() => {
    setMemo(guide.memo ?? "")
    lastSaved.current = guide.memo ?? ""
  }, [guide.tripId, guide.memo])

  useEffect(() => {
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [])

  function persist(next: string) {
    if (!onSaveMemo || next === lastSaved.current) return
    lastSaved.current = next
    void onSaveMemo(next)
      .then(() => setSaveMsg("메모를 저장했습니다."))
      .catch((e) => {
        lastSaved.current = memo
        setSaveMsg(e instanceof Error ? e.message : "메모 저장 실패")
      })
  }

  function onChange(value: string) {
    setMemo(value)
    setSaveMsg(null)
    if (!onSaveMemo) return
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(() => persist(value), 800)
  }

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-white">
      <div className="shrink-0 bg-[#1f8a56] px-5 pb-6 pt-7">
        <div className="mb-3.5 flex items-center gap-1.5">
          <span className="size-1.5 rounded-[3px] bg-white/50" />
          <span className="size-1.5 rounded-[3px] bg-white/30" />
          <span className="size-1.5 rounded-[3px] bg-white/15" />
          <span className="h-px flex-1 bg-white/20" />
        </div>
        <span className="inline-block rounded-[4px] bg-white/15 px-2 py-[3px] text-[9px] font-bold tracking-[2px] text-white/70">
          TRAVEL SCHEDULE
        </span>
        <p className="mt-3.5 text-[26px] font-black tracking-[-0.5px] text-white">{guide.title}</p>
        <div className="mt-3 inline-flex items-center gap-1.5 rounded-[20px] border border-white/20 bg-white/10 px-3 py-1.5">
          <Calendar size={10} className="text-white/80" />
          <p className="text-[11px] font-medium text-white/80">{innerDatePill(guide)}</p>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-white">
        <div className="px-5 py-5">
          {guide.stops.length === 0 ? (
            <p className="py-8 text-center text-[13px] text-ink-muted">등록된 장소가 없어요.</p>
          ) : (
            guide.stops.map((stop, index) => (
              <GuideScheduleItem
                key={`${stop.position}-${stop.placeName}`}
                stop={stop}
                index={index + 1}
                showConnector={index < guide.stops.length - 1}
              />
            ))
          )}
        </div>
        <div className="h-px w-full bg-[#e8edf5]" />
        <div className="flex flex-col gap-3 p-5">
          <div className="flex items-center gap-2">
            <Pencil size={14} className="text-ink" />
            <p className="text-[12px] font-extrabold tracking-[1px] text-ink">MEMO</p>
          </div>
          {memoReadOnly ? (
            <div className="min-h-[100px] rounded-[10px] border border-dashed border-[#c3ccd8] p-3 text-[11px] text-ink-soft">
              {memo.trim() ? memo : "작성된 메모가 없습니다."}
            </div>
          ) : (
            <textarea
              value={memo}
              onChange={(e) => onChange(e.target.value)}
              onBlur={() => persist(memo)}
              placeholder="여행 메모를 입력하세요..."
              className="min-h-[100px] w-full resize-none rounded-[10px] border border-dashed border-[#c3ccd8] p-3 text-[11px] text-ink outline-none placeholder:text-[#999]"
            />
          )}
          {saveMsg ? <p className="text-[11px] text-ink-muted">{saveMsg}</p> : null}
        </div>
      </div>
    </div>
  )
}
