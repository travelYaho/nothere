/**
 * STEP10 — 최종 여행 일정
 * Figma: 최종 여행 일정 프레임. 점검이 끝난 일정을 타임라인으로 보고
 * 저장·공유·가이드북 만들기로 이어진다.
 */
import { useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Doc } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { BasicHeader } from "@/components/layout/navigation"
import { fetchAnalysis, fetchTripGuide, useConfirmGuide } from "@/features/recommendation"
import type { AnalysisItem, GuideResponse } from "@/features/recommendation"
import { getTripDetail } from "@/features/trips/api/tripsApi"
import type { TripDetailResponse, TripPlaceDetail } from "@/features/trips/types"
import { formatVisitTime } from "@/features/trips/utils/placeOrder"
import { getAccessToken } from "@/store/sessionStore"
import { ApiError } from "@/types/api"
import { formatDottedDateWithWeekday } from "@/utils/date"

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) {
    if (/failed to fetch|network/i.test(err.message)) {
      return "서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."
    }
    return err.message
  }
  return "요청 중 문제가 발생했습니다."
}

function congestionPhrase(item: AnalysisItem | undefined): string {
  const level = item?.level
  if (level === "high" && item?.isFixed) return "혼잡 예상 (유지 선택)"
  if (level === "high") return "혼잡 예상"
  if (level === "mid" || level === "medium") return "보통 예상"
  if (level === "low") return "여유 예상"
  return "예측 정보 없음"
}

function stopMeta(
  place: TripPlaceDetail,
  analysis: AnalysisItem | undefined,
  replacedFrom: string | null,
): string {
  const stay = place.durationMinutes != null ? `체류 ${place.durationMinutes}분` : null
  const rest = replacedFrom ? `원래: ${replacedFrom}` : congestionPhrase(analysis)
  return [stay, rest].filter(Boolean).join(" · ")
}

export default function ConfirmTrip() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { doConfirm, share } = useConfirmGuide(tripId)

  const [trip, setTrip] = useState<TripDetailResponse | null>(null)
  const [guide, setGuide] = useState<GuideResponse | null>(null)
  const [analysisById, setAnalysisById] = useState<Record<string, AnalysisItem>>({})
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [footerMsg, setFooterMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!tripId) return
    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const token = await getAccessToken()
        const detail = await getTripDetail(tripId!)
        if (cancelled) return
        setTrip(detail)

        if (token) {
          const [guideResult, analysisResult] = await Promise.allSettled([
            fetchTripGuide(token, tripId!),
            fetchAnalysis(token, tripId!),
          ])
          if (cancelled) return
          if (guideResult.status === "fulfilled") setGuide(guideResult.value)
          if (analysisResult.status === "fulfilled") {
            setAnalysisById(
              Object.fromEntries(analysisResult.value.items.map((item) => [item.tripPlaceId, item])),
            )
          }
        }
        setLoadError(null)
      } catch (err) {
        if (!cancelled) setLoadError(toErrorMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [tripId])

  const places = trip?.places ?? []
  const replacedCount = useMemo(
    () => (guide?.stops ?? []).filter((stop) => stop.wasReplaced).length,
    [guide],
  )
  const totalTravelMin = useMemo(
    () =>
      (guide?.stops ?? []).reduce((sum, stop) => sum + (stop.travelToNext?.durationMin ?? 0), 0),
    [guide],
  )

  const metaLine = trip
    ? [
        trip.travelDate ? formatDottedDateWithWeekday(trip.travelDate) : null,
        trip.regionName,
        `${places.length}곳`,
        totalTravelMin > 0 ? `이동 ${totalTravelMin}분` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : ""

  const onSave = async () => {
    if (!tripId) return
    setBusy(true)
    setError(null)
    setFooterMsg(null)
    try {
      if (trip?.status !== "confirmed") await doConfirm()
      navigate(`/trips/${tripId}/saved`)
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const onShare = async () => {
    setBusy(true)
    setError(null)
    setFooterMsg(null)
    try {
      if (trip?.status !== "confirmed") await doConfirm()
      const res = await share()
      const url = res.absoluteUrl ?? `${window.location.origin}${res.url}`
      await navigator.clipboard.writeText(url)
      setFooterMsg("공유 링크를 복사했습니다.")
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const onMakeGuidebook = async () => {
    if (!tripId) return
    setBusy(true)
    setError(null)
    try {
      if (trip?.status !== "confirmed") await doConfirm()
      navigate(`/trips/${tripId}/guide`)
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      <BasicHeader
        title="최종 여행 일정"
        onBack={() => navigate(-1)}
        right={
          <button
            type="button"
            className="text-[13px] font-bold leading-5 text-primary"
            onClick={() => tripId && navigate(`/trips/${tripId}/remaining`)}
          >
            일정 수정
          </button>
        }
      />

      {loading && (
        <div className="flex flex-1 items-center justify-center text-[13px] text-ink-muted">
          불러오는 중...
        </div>
      )}

      {!loading && loadError && (
        <div className="flex flex-1 items-center justify-center px-6 text-center text-[13px] font-medium text-ink-soft">
          {loadError}
        </div>
      )}

      {!loading && !loadError && trip && (
        <>
          <div className="flex flex-1 flex-col overflow-y-auto px-4 pb-4">
            <div className="px-1 pt-2">
              <h2 className="text-[17px] font-extrabold leading-[26px] tracking-[-0.34px] text-ink">
                {trip.title}
              </h2>
              <p className="pt-1 text-[12px] font-medium leading-[18px] text-ink-muted">{metaLine}</p>
            </div>

            {replacedCount > 0 && (
              <div className="mt-3 rounded-2xl bg-[#E8F6EE] px-4 py-3">
                <p className="text-[13px] font-bold leading-[21px] text-[#1F8A56]">
                  좀 더 여유로운 장소로 변경되었어요
                </p>
                <p className="text-[11px] font-medium leading-4 text-[#4A8A6C]">
                  혼잡이 예상된 {replacedCount}곳을 가까운 대안으로 바꿨습니다.
                </p>
              </div>
            )}

            <div className="relative mt-3 flex h-[86px] w-full items-center justify-center rounded-2xl border-[0.667px] border-dashed border-[#D3DBE6] bg-[#EEF1F6]">
              <span className="text-[12px] font-medium leading-[18px] text-ink-ghost">
                MAP AREA — 최종 경로
              </span>
            </div>

            {places.length === 0 ? (
              <p className="py-10 text-center text-[13px] text-ink-muted">등록된 장소가 없어요.</p>
            ) : (
              <div className="flex flex-col pt-4 pl-1">
                {places.map((place, index) => {
                  const stop = guide?.stops[index]
                  const analysis = analysisById[place.tripPlaceId]
                  const isFirst = index === 0
                  const isLast = index === places.length - 1
                  const travelMin = stop?.travelToNext?.durationMin
                  const replacedFrom = stop?.replacedFrom ?? null
                  const wasReplaced = Boolean(stop?.wasReplaced && replacedFrom)

                  return (
                    <div key={place.tripPlaceId} className="flex flex-col">
                      <div className="flex items-start gap-3">
                        <div className="flex w-2.5 shrink-0 flex-col items-center self-stretch">
                          <span
                            className={[
                              "mt-1 size-2.5 shrink-0 rounded-full",
                              isFirst ? "bg-primary" : "bg-[#C3CCD8]",
                            ].join(" ")}
                          />
                          {!isLast && <span className="mt-1 w-px flex-1 bg-[#DBE2EC]" />}
                        </div>
                        <div className="min-w-0 flex-1 pb-1">
                          <p className="text-[11px] font-semibold leading-4 text-ink-faint">
                            {formatVisitTime(place.visitTime || stop?.visitTime || null) || "--:--"}
                          </p>
                          <div className="flex items-center gap-1.5">
                            <p className="truncate text-[14px] font-bold leading-[21px] text-ink">
                              {place.name}
                            </p>
                            {wasReplaced && (
                              <span className="rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold leading-[15px] text-primary">
                                변경됨
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] font-medium leading-4 text-ink-faint">
                            {stopMeta(place, analysis, wasReplaced ? replacedFrom : null)}
                          </p>
                        </div>
                      </div>
                      {!isLast && (
                        <p className="py-1 pl-[26px] text-[11px] font-medium leading-4 text-ink-ghost">
                          {travelMin != null ? `↓ 이동 ${travelMin}분` : "↓ 이동"}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {error && <p className="pt-3 text-[13px] text-ink-soft">{error}</p>}
            {footerMsg && <p className="pt-3 text-[12px] text-ink-muted">{footerMsg}</p>}
          </div>

          <div className="border-t-[0.667px] border-line-soft bg-white/95 px-4 pb-6 pt-3">
            <div className="flex gap-2.5">
              <Button
                variant="ghost"
                disabled={busy}
                onClick={() => void onSave()}
                className="h-[54px] w-[76px] shrink-0 px-4 text-[15px] font-bold"
              >
                저장
              </Button>
              <Button
                variant="ghost"
                disabled={busy}
                onClick={() => void onShare()}
                className="h-[54px] w-[76px] shrink-0 px-4 text-[15px] font-bold"
              >
                공유
              </Button>
              <button
                type="button"
                disabled={busy || places.length === 0}
                onClick={() => void onMakeGuidebook()}
                className="inline-flex h-[54px] flex-1 items-center justify-center gap-2 rounded-2xl bg-primary text-[16px] font-extrabold tracking-[-0.16px] text-primary-foreground shadow-[var(--shadow-primary)] transition-[transform,filter,opacity] active:scale-[0.99] disabled:pointer-events-none disabled:opacity-45"
              >
                <Doc size={16} />
                {busy ? "처리 중…" : "가이드북 만들기"}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
