import type { GuideResponse } from "@/features/recommendation/types/part3"
import { formatDottedDate, formatDottedDateWithWeekday } from "@/utils/date"

const CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

export function circledIndex(index: number): string {
  if (index >= 1 && index <= 20) return CIRCLED[index - 1] ?? String(index)
  return String(index)
}

export function shortPlaceLabel(region: {
  cityName?: string | null
  districtName?: string | null
  regionName?: string | null
}): { city: string; district: string } {
  const city = region.cityName?.trim() || region.regionName?.split(/\s+/)[0] || ""
  const district = region.districtName?.trim() || ""
  return { city, district }
}

export function guideKicker(district: string, city: string): string {
  const raw = (district || city || "TRIP").replace(/[구군]$/, "")
  return `${raw} GUIDE`.toUpperCase()
}

export function regionLine(city: string, district: string): string {
  return [city, district].filter(Boolean).join(" ")
}

export function travelMinutes(guide: GuideResponse): number {
  if (typeof guide.totalTravelMin === "number") return guide.totalTravelMin
  return guide.stops.reduce((sum, stop) => sum + (stop.travelToNext?.durationMin ?? 0), 0)
}

export function coverMetaLine(guide: GuideResponse): string {
  const { city, district } = shortPlaceLabel(guide)
  const parts = [
    guide.travelDate ? formatDottedDate(guide.travelDate) : null,
    regionLine(city, district) || guide.regionName || null,
    `이동 ${travelMinutes(guide)}분`,
  ]
  return parts.filter(Boolean).join(" · ")
}

export function innerDatePill(guide: GuideResponse): string {
  const datePart = guide.travelDate ? formatDottedDateWithWeekday(guide.travelDate) : null
  const parts = [
    datePart,
    `코스 ${guide.stops.length}곳`,
    `이동 ${travelMinutes(guide)}분`,
  ]
  return parts.filter(Boolean).join(" · ")
}
