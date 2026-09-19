import type { CongestionLevel } from "@/components/common/primitives"
import type { CompareCandidate } from "../types/part3"

export function candidateLetter(index: number): string {
  return String.fromCharCode(65 + index)
}

export function shortCongestionLabel(level: CongestionLevel): string {
  if (level === "high") return "혼잡 예상"
  if (level === "medium") return "보통"
  if (level === "low") return "여유"
  return "정보 없음"
}

export function congestionTextClass(level: CongestionLevel): string {
  if (level === "high") return "text-congestion-high"
  if (level === "medium") return "text-congestion-medium"
  if (level === "low") return "text-congestion-low"
  return "text-ink-faint"
}

export function formatExtraMinutes(minutes: number | null | undefined): string | null {
  if (minutes == null) return null
  return minutes >= 0 ? `+${minutes}분` : `${minutes}분`
}

export function formatTravelChange(
  originalMinutes: number | null | undefined,
  travelMinutes: number | null | undefined,
  extraMinutes: number | null | undefined,
): string | null {
  if (originalMinutes != null && travelMinutes != null) {
    const extra = formatExtraMinutes(extraMinutes)
    return extra ? `${originalMinutes}분 → ${travelMinutes}분 (${extra})` : `${originalMinutes}분 → ${travelMinutes}분`
  }
  if (travelMinutes != null) return `${travelMinutes}분`
  return formatExtraMinutes(extraMinutes)
}

export function formatNeighborDistance(
  prevM: number | null | undefined,
  nextM: number | null | undefined,
): string | null {
  if (prevM == null && nextM == null) return null
  const fmt = (meters: number) => (meters / 1000).toFixed(1)
  if (prevM != null && nextM != null) return `${fmt(prevM)} / ${fmt(nextM)}km`
  return `${fmt((prevM ?? nextM)!)}km`
}

export function districtFromAddress(address: string | null | undefined): string | null {
  if (!address) return null
  const match = address.match(/([가-힣]+(?:구|군))/)
  return match?.[1] ?? null
}

export function reasonLines(candidate: CompareCandidate): string[] {
  const lines: string[] = []
  if (candidate.experienceScore >= 0.35) {
    lines.push("기존 방문 목적과 유사해요")
  }
  if (candidate.extraMinutes != null && candidate.extraMinutes <= 20) {
    lines.push("앞뒤 일정에서 크게 벗어나지 않아요")
  }
  if (lines.length > 0) return lines
  if (!candidate.reasonText) return []
  return candidate.reasonText
    .split(/(?<=요)\s+|(?<=다[.!]?)\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2)
}

export function kakaoMapSearchUrl(placeName: string): string {
  return `https://map.kakao.com/link/search/${encodeURIComponent(placeName)}`
}
