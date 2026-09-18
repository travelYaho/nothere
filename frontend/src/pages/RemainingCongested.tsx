/**
 * 일정 점검 결과 — STEP4 분석 결과를 전체 장소 목록으로 보여주고,
 * 혼잡한 장소는 카드에서 바로 대안보기/유지를 할 수 있게 한다.
 */
import { useEffect, useRef, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { CongestionCard } from "@/components/common/cards"
import { Button } from "@/components/common/primitives"
import { BasicHeader } from "@/components/layout/navigation"
import {
  fetchAnalysis,
  keepTripPlace,
  toUiCongestion,
  useAccessToken,
  useRunAnalysis,
} from "@/features/recommendation"
import type { AnalysisItem } from "@/features/recommendation"
import { useSession } from "@/store/sessionStore"

type LocationState = {
  analysis?: { items: AnalysisItem[] }
} | null

function isCrowdedPending(item: AnalysisItem) {
  return item.level === "high" && item.resolutionStatus === "pending" && !item.isFixed
}

function needsFreshAnalysis(items: AnalysisItem[]) {
  return items.some((item) => !item.analyzedAt)
}

export default function RemainingCongested() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const token = useAccessToken()
  const { isLoading: sessionLoading } = useSession()
  const { run: runAnalysis } = useRunAnalysis(tripId)

  const [items, setItems] = useState<AnalysisItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set())
  const [keepErrors, setKeepErrors] = useState<Record<string, string>>({})
  const firstCrowdedRef = useRef<HTMLDivElement>(null)

  // location.state는 새로고침에도 남아 있을 수 있다. 재렌더/재실행 때마다 다시 읽으면
  // 그 사이 지워졌는지에 따라 분기가 흔들릴 수 있으므로, 이 마운트에서 처음 읽은 값을
  // 고정해서 쓰고 곧바로(useEffect) 지운다 — 이후 새로고침에서는 다시 쓰이지 않는다.
  const [pendingState] = useState<LocationState>(() => location.state as LocationState)

  useEffect(() => {
    if (pendingState) {
      navigate(location.pathname, { replace: true, state: null })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!tripId) return

    // 로딩 화면(TripAnalysisLoading)이 이미 최신 분석 결과를 들고 넘어온 경우 — 재조회 없음.
    if (pendingState?.analysis) {
      setItems(pendingState.analysis.items)
      setLoading(false)
      return
    }

    // 세션(토큰) 로딩이 끝나기 전에 호출하면 항상 401로 실패한다 — 기다렸다가 부른다.
    if (sessionLoading) return

    let cancelled = false
    setLoading(true)
    setError(null)

    // 교체 후에는 저장된 분석만 GET한다. 전체 POST 재분석은 다른 장소 혼잡도를 덮어쓸 수 있다.
    // 분석이 비어 있는 장소(교체분 unknown 등)만 있을 때 재분석을 돌리고, 백엔드는 성공 분을 건너뛴다.
    fetchAnalysis(token, tripId)
      .then(async (result) => {
        if (!needsFreshAnalysis(result.items)) return result
        const rerun = await runAnalysis()
        if (rerun) return rerun
        return result
      })
      .then((result) => {
        if (cancelled) return
        setItems(result.items)
      })
      .catch((e) => {
        if (cancelled) return
        setError(e instanceof Error ? e.message : "조회 실패")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    // 이 실행이 끝나기 전에 재실행되거나(예: 세션 로딩 완료) 화면을 벗어나면, 늦게 도착한
    // 응답이 이후 상태를 덮어쓰지 않도록 막는다.
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId, sessionLoading, token])

  const handleKeep = async (item: AnalysisItem) => {
    if (savingIds.has(item.tripPlaceId)) return
    setSavingIds((prev) => new Set(prev).add(item.tripPlaceId))
    setKeepErrors((prev) => {
      if (!(item.tripPlaceId in prev)) return prev
      const next = { ...prev }
      delete next[item.tripPlaceId]
      return next
    })
    try {
      await keepTripPlace(item.tripPlaceId)
      setItems((prev) =>
        prev
          ? prev.map((i) => (i.tripPlaceId === item.tripPlaceId ? { ...i, isFixed: true } : i))
          : prev,
      )
    } catch (e) {
      setKeepErrors((prev) => ({
        ...prev,
        [item.tripPlaceId]: e instanceof Error ? e.message : "저장 실패",
      }))
    } finally {
      setSavingIds((prev) => {
        const next = new Set(prev)
        next.delete(item.tripPlaceId)
        return next
      })
    }
  }

  const crowdedCount = (items ?? []).filter(isCrowdedPending).length
  const firstCrowdedId = (items ?? []).find(isCrowdedPending)?.tripPlaceId

  const goConfirm = () => navigate(`/trips/${tripId}/confirm`)
  const scrollToRemaining = () => {
    firstCrowdedRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })
  }

  const placeList = items
    ? items.map((item) => {
        const showActions = item.resolutionStatus === "pending" && !item.isFixed
        const isFirstCrowded = item.tripPlaceId === firstCrowdedId
        return (
          <div key={item.tripPlaceId} ref={isFirstCrowded ? firstCrowdedRef : undefined}>
            <CongestionCard
              time={item.visitTime ?? ""}
              place={item.placeName}
              level={toUiCongestion(item.level)}
              showActions={showActions}
              replacedFrom={item.replacedFrom}
              onAlternative={() =>
                navigate(`/trips/${tripId}/places/${item.tripPlaceId}/purpose`)
              }
              onKeep={() => void handleKeep(item)}
            />
            {keepErrors[item.tripPlaceId] && (
              <p className="mt-1 text-[12px] text-congestion-high">
                {keepErrors[item.tripPlaceId]}
              </p>
            )}
          </div>
        )
      })
    : null

  return (
    <div className="relative flex min-h-screen flex-1 flex-col">
      <BasicHeader
        title="일정 점검 결과"
        onBack={() => navigate(-1)}
        right={
          <button
            type="button"
            className="text-[13px] font-bold leading-5 text-primary"
            // replace: 장소를 고쳐서 다시 점검하면 이 결과는 낡은 값이 되므로,
            // 뒤로가기가 이 결과 화면으로 다시 돌아오지 않게 히스토리에서 대체한다.
            onClick={() => navigate(`/trips/${tripId}/places`, { replace: true })}
          >
            일정 수정
          </button>
        }
      />

      {loading && <p className="px-5 pt-2 text-[13px] text-ink-muted">확인 중…</p>}
      {error && <p className="px-5 pt-2 text-[13px] text-congestion-high">{error}</p>}

      {!loading && !error && items && (
        <>
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pt-2">
            <div className="rounded-2xl bg-[#E8F6EE] px-4 py-[14px]">
              <p className="text-[15px] font-extrabold leading-[22.5px] text-[#1F8A56]">
                {crowdedCount > 0 ? `남은 혼잡 ${crowdedCount}곳` : "모든 혼잡 장소를 확인했어요"}
              </p>
              {crowdedCount > 0 && (
                <p className="pt-0.5 text-[12px] font-medium leading-[18px] text-[#4A8A6C]">
                  계속 점검하거나 지금 확정할 수 있어요
                </p>
              )}
            </div>

            <div className="flex flex-col gap-2.5 pt-3">{placeList}</div>

            <p className="py-4 text-center text-[11px] leading-[16.5px] text-ink-ghost">
              교체 후 이동시간·집중도는 자동 재계산됩니다.
            </p>
          </div>

          <div className="border-t-[0.667px] border-line-soft bg-white/95 px-4 pb-6 pt-3">
            <div className="flex gap-2.5">
              {crowdedCount > 0 && (
                <Button
                  variant="ghost"
                  onClick={scrollToRemaining}
                  className="h-[54px] min-w-0 flex-1 px-4 text-[15px] font-bold"
                >
                  계속 점검하기
                </Button>
              )}
              <Button
                variant="accent"
                onClick={goConfirm}
                className="h-[54px] min-w-0 flex-1"
              >
                현재 일정으로 확정
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
