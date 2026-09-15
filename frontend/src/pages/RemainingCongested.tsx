/**
 * 일정 점검 결과 — STEP4 분석 결과를 전체 장소 목록으로 보여주고,
 * 혼잡한 장소는 카드에서 바로 대안보기/유지를 할 수 있게 한다.
 * 장소를 한 곳이라도 교체한 뒤에는 Figma 점검 결과(교체 후) 레이아웃을 쓴다.
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
  reanalyze?: boolean
} | null

function isCrowdedPending(item: AnalysisItem) {
  return item.level === "high" && item.resolutionStatus === "pending" && !item.isFixed
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

    // 장소 교체 직후 재진입이면(옛 분석이 지워졌으므로) 재분석(POST), 아니면 저장된 결과만 조회(GET).
    const request = pendingState?.reanalyze
      ? runAnalysis().then((result) => {
          if (result) return result
          throw new Error("분석에 실패했습니다. 다시 시도해 주세요.")
        })
      : fetchAnalysis(token, tripId)

    request
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
  const hasReplaced = (items ?? []).some((item) => Boolean(item.wasReplaced && item.replacedFrom))
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
            className="text-[13px] font-bold text-primary"
            onClick={() => navigate(`/trips/${tripId}/places`)}
          >
            일정 수정
          </button>
        }
      />

      {loading && <p className="px-5 pt-2 text-[13px] text-ink-muted">확인 중…</p>}
      {error && <p className="px-5 pt-2 text-[13px] text-congestion-high">{error}</p>}

      {!loading && !error && items && hasReplaced && (
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
              <Button
                variant="ghost"
                onClick={scrollToRemaining}
                className="h-[54px] min-w-0 flex-1 px-4 text-[15px] font-bold"
              >
                계속 점검하기
              </Button>
              <Button
                onClick={goConfirm}
                className="h-[54px] min-w-0 flex-1 text-[16px] font-extrabold"
              >
                현재 일정으로 확정
              </Button>
            </div>
          </div>
        </>
      )}

      {!loading && !error && items && !hasReplaced && (
        <div className="flex flex-1 flex-col gap-4 px-5 pb-10 pt-2">
          <div>
            <p className="text-[14px] font-bold text-ink">
              {crowdedCount > 0
                ? `혼잡이 예상되는 장소 ${crowdedCount}곳`
                : "모든 혼잡 장소를 확인했어요"}
            </p>
            {crowdedCount > 0 && (
              <p className="mt-1 text-[13px] text-ink-muted">
                한 곳씩 가까운 대안으로 바꿀 수 있어요
              </p>
            )}
          </div>

          <div className="flex flex-col gap-3">{placeList}</div>

          <p className="text-[12px] text-ink-faint">
            일정표는 실시간 정보가 아니며 실제 상황과 다를 수 있어요.
          </p>

          <Button block onClick={goConfirm}>
            현재 일정으로 확정
          </Button>
        </div>
      )}
    </div>
  )
}
