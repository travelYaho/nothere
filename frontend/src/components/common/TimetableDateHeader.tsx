import { formatTimetableDate } from "@/utils/date"

export function TimetableDateHeader({ travelDate }: { travelDate: string | null | undefined }) {
  if (!travelDate) return null
  const dateParts = formatTimetableDate(travelDate)
  return (
    <div>
      <h2 className="text-[48px] font-extrabold leading-none tracking-[-1px] text-ink">
        {dateParts.monthLabel}
      </h2>
      <div className="mt-1 flex items-end gap-2">
        <p className="text-[40px] font-extrabold leading-none tracking-[-1.2px] text-ink">
          {dateParts.dayPadded}
        </p>
        <p className="pb-1 text-[13px] font-medium italic text-ink-muted">{dateParts.weekdayLabel}</p>
      </div>
    </div>
  )
}
