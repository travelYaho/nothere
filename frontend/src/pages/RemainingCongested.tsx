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

// analysisStatus는 고정/교체 여부와 무관하게 그 자체로 참이다 — "유지"나 "교체"를
// 선택했다는 사실이 "분석이 성공했다"는 뜻은 아니다(코드 리뷰로 발견, 2026-09-19). 예를
// 들어 예전에 혼잡(high)으로 떠서 "유지"한 장소도, 이후 일정이 바뀌어 재분석이 걸리면
// (trip.needs_reanalysis) 다시 분석되고 이번엔 API 호출이 실패할 수 있다 — 그런데도
// isFixed만 보고 "이미 처리됨"으로 묶어 실패 집계에서 빼면, 사용자는 그 장소가 실제로는
// 한 번도 성공적으로 분석되지 못했다는 걸 알 방법이 없다. 그래서 이 두 함수는
// resolutionStatus/isFixed를 전혀 보지 않고 analysisStatus만으로 판단한다.
function isFailedAnalysis(item: AnalysisItem) {
  return item.analysisStatus === "failed"
}
function isUnavailableAnalysis(item: AnalysisItem) {
  return item.analysisStatus === "unavailable"
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
  // retrying/retryError는 이 훅 하나가 트립 전체 재분석을 책임진다 — 카드 하나만 골라
  // 재시도하는 API가 없어서, 실패한 카드 중 아무거나 눌러도 실제로는 트립의 모든
  // 미해결(failed/unavailable) 장소가 함께 재시도된다. 백엔드 run_analysis()는 평소엔
  // analysis_status="success"인 장소를 건너뛰지만, trip.needs_reanalysis가 켜져 있으면
  // (일정 변경 등) 그 예외로 성공한 장소까지 포함해 전체를 다시 분석한다 — "성공한 장소는
  // 절대 재분석하지 않는다"는 항상 참은 아니다(코드 리뷰로 표현 교정, 2026-09-19).
  const { run: runAnalysis, loading: retrying, error: retryError } = useRunAnalysis(tripId)

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

  const handleRetry = async () => {
    const result = await runAnalysis()
    if (result) setItems(result.items)
  }

  const crowdedCount = (items ?? []).filter(isCrowdedPending).length
  const failedCount = (items ?? []).filter(isFailedAnalysis).length
  const unavailableCount = (items ?? []).filter(isUnavailableAnalysis).length
  const notAnalyzedCount = failedCount + unavailableCount
  const firstCrowdedId = (items ?? []).find(isCrowdedPending)?.tripPlaceId

  const goConfirm = () => navigate(`/trips/${tripId}/confirm`)
  const scrollToRemaining = () => {
    firstCrowdedRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })
  }

  const placeList = items
    ? items.map((item) => {
        const showActions = item.resolutionStatus === "pending" && !item.isFixed
        const isFirstCrowded = item.tripPlaceId === firstCrowdedId
        const analysisFailed = item.analysisStatus === "failed"
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
              analysisFailed={analysisFailed}
              retrying={retrying}
              onRetry={analysisFailed ? () => void handleRetry() : undefined}
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
            <div
              className={[
                "rounded-2xl px-4 py-[14px]",
                crowdedCount === 0 && notAnalyzedCount > 0 ? "bg-surface-chip" : "bg-[#E8F6EE]",
              ].join(" ")}
            >
              <p
                className={[
                  "text-[15px] font-extrabold leading-[22.5px]",
                  crowdedCount === 0 && notAnalyzedCount > 0 ? "text-ink" : "text-[#1F8A56]",
                ].join(" ")}
              >
                {crowdedCount > 0
                  ? `남은 혼잡 ${crowdedCount}곳`
                  : notAnalyzedCount > 0
                    ? `분석하지 못한 장소 ${notAnalyzedCount}곳`
                    : "모든 혼잡 장소를 확인했어요"}
              </p>
              {/* 세 갈래로 나눈다 — 재시도 버튼은 analysisStatus==="failed" 카드에만 있다.
                  unavailable(지역코드 없음, 검수 대기 등)은 영구히 고정된 상태가 아니라
                  예측 데이터 갱신이나 매핑 검수 이후 달라질 수 있지만, 지금 다시 누른다고
                  바로 해결된다고 보장할 수 없어 버튼을 주지 않는다(코드 리뷰로 표현 교정,
                  2026-09-19 — "재시도해도 안 바뀌는 상태"는 과장이었다). 안내 문구가 버튼의
                  실제 존재 여부와 어긋나면 안 된다(2026-09-19, 코드 리뷰로 발견 —
                  unavailable만 있을 때도 "다시 시도할 수 있어요"라고 안내해 버튼 없는 화면을
                  만들고 있었다). */}
              {crowdedCount > 0 ? (
                <p className="pt-0.5 text-[12px] font-medium leading-[18px] text-[#4A8A6C]">
                  계속 점검하거나 지금 확정할 수 있어요
                  {notAnalyzedCount > 0 && ` · 분석하지 못한 장소 ${notAnalyzedCount}곳`}
                </p>
              ) : failedCount > 0 ? (
                <p className="pt-0.5 text-[12px] font-medium leading-[18px] text-ink-faint">
                  아래 카드에서 다시 시도할 수 있어요
                </p>
              ) : (
                unavailableCount > 0 && (
                  <p className="pt-0.5 text-[12px] font-medium leading-[18px] text-ink-faint">
                    일부 장소는 혼잡도 정보를 제공하지 못해요
                  </p>
                )
              )}
            </div>
            {retryError && (
              <p className="pt-2 text-[12px] text-congestion-high">{retryError}</p>
            )}

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
