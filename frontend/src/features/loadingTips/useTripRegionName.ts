import { useEffect, useState } from "react"
import { getTripDetail } from "@/features/trips"

/**
 * 일정의 지역명을 조회한다. 실패하거나 늦어져도 화면 흐름에는 영향이 없다(지역 문구만 빠진다).
 * 결과를 tripId와 함께 저장하고 현재 일정과 일치할 때만 돌려줘서, 일정이 바뀌면 이전 일정의
 * 지역명이 남지 않는다(새 일정 조회 중이거나 실패하면 null → 공통 문구).
 */
export function useTripRegionName(tripId: string | undefined, enabled: boolean): string | null {
  const [result, setResult] = useState<{ tripId: string; regionName: string } | null>(null)

  useEffect(() => {
    if (!tripId || !enabled) return
    let cancelled = false
    getTripDetail(tripId)
      .then((detail) => {
        if (!cancelled) setResult({ tripId, regionName: detail.regionName })
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [tripId, enabled])

  return result !== null && result.tripId === tripId ? result.regionName : null
}
