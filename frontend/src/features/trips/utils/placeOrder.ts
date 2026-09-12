import type { TripPlaceDetail } from "@/features/trips/types"

type TimedPlace = { visitTime: string | null }

/**
 * 시간이 설정된 장소끼리만 오름차순으로 재배열하고, 그 장소들이 원래
 * 차지하던 자리(index)에 도로 끼워 넣는다 — 시간 미설정 장소는 드래그로
 * 옮긴 자리를 그대로 유지한 채, 시간이 있는 장소만 "빠른 시간대가 앞"이
 * 되도록 자동 정렬하기 위해서다.
 */
export function sortPlacesForDisplay<T extends TimedPlace>(places: T[]): T[] {
  const result = [...places]
  const timedIndices: number[] = []
  result.forEach((place, index) => {
    if (place.visitTime) timedIndices.push(index)
  })
  const timedSorted = timedIndices
    .map((index) => result[index])
    .sort((a, b) => (a.visitTime! < b.visitTime! ? -1 : a.visitTime! > b.visitTime! ? 1 : 0))
  timedIndices.forEach((index, i) => {
    result[index] = timedSorted[i]
  })
  return result
}

/** 시간이 있는 장소끼리 오름차순인지 확인한다. 미지정 장소는 무시한다. */
export function isChronologicalVisitOrder<T extends TimedPlace>(places: T[]): boolean {
  let lastTime: string | null = null
  for (const place of places) {
    if (!place.visitTime) continue
    if (lastTime !== null && place.visitTime < lastTime) return false
    lastTime = place.visitTime
  }
  return true
}

export function applyReorder<T>(items: T[], fromIndex: number, toIndex: number): T[] {
  if (fromIndex === toIndex) return items
  const next = [...items]
  const [moved] = next.splice(fromIndex, 1)
  next.splice(toIndex, 0, moved)
  return next
}

export function withVisitOrder(places: TripPlaceDetail[]): TripPlaceDetail[] {
  return places.map((place, index) => ({ ...place, visitOrder: index + 1 }))
}

export function formatVisitTime(visitTime: string | null): string {
  return visitTime ? visitTime.slice(0, 5) : ""
}
