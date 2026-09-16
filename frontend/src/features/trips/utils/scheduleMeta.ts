/** Home.tsx/Bookmarks.tsx가 공유하는 일정 카드 부제 포맷터. */
import type { TripSummary, ScheduleSummary } from "@/features/trips/types"

function formatKoreanDate(travelDate: string): string {
  const d = new Date(`${travelDate}T00:00:00`)
  if (Number.isNaN(d.getTime())) return travelDate
  return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`
}

const IN_PROGRESS_STATUSES = new Set(["draft", "analyzed", "editing"])

/** "2026년 8월 14일 · 4곳 등록" / 확정된 일정이면 뒤에 "· 확정됨" 추가. */
export function formatScheduleMeta(schedule: TripSummary | ScheduleSummary): string {
  const parts: string[] = []
  if (schedule.travelDate) parts.push(formatKoreanDate(schedule.travelDate))
  parts.push(`${schedule.placeCount}곳 등록`)
  if (!IN_PROGRESS_STATUSES.has(schedule.status)) parts.push("확정됨")
  return parts.join(" · ")
}
