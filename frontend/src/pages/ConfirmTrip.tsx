/**
 * STEP9 — 최종 일정 확정
 * 전체 일정을 타임테이블로 확인하고, 순서를 바꾼 뒤 확정한다.
 */
import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Grip } from "@/components/common/icons"
import { AlertDialog } from "@/components/feedback/modals"
import { FlowHeader } from "@/components/layout/navigation"
import { useConfirmGuide } from "@/features/recommendation"
import { getTripPlacePurpose } from "@/features/trips/api/purposeApi"
import { reorderTripPlaces, updateTripPlaceVisit } from "@/features/trips/api/placesApi"
import { getTripDetail } from "@/features/trips/api/tripsApi"
import { useLongPressReorder } from "@/features/trips/hooks/useLongPressReorder"
import type { PurposeTag, TripPlaceDetail } from "@/features/trips/types"
import {
  applyReorder,
  formatVisitTime,
  isChronologicalVisitOrder,
  sortPlacesForDisplay,
  withVisitOrder,
} from "@/features/trips/utils/placeOrder"
import { ApiError } from "@/types/api"
import { formatTimetableDate } from "@/utils/date"

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

function UnsetVisitTimeButton({
  disabled,
  onSelect,
}: {
  disabled?: boolean
  onSelect: (time: string) => void
}) {
  return (
    <label className="relative inline-flex h-7 w-[52px] shrink-0 cursor-pointer items-center justify-center rounded-md border border-dashed border-line-chip bg-surface text-[13px] font-bold tabular-nums text-ink-ghost">
      --:--
      <input
        type="time"
        disabled={disabled}
        aria-label="방문 시간 설정"
        onPointerDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => {
          const value = e.target.value
          if (value) onSelect(value)
        }}
        className="absolute inset-0 cursor-pointer opacity-0"
      />
    </label>
  )
}

export default function ConfirmTrip() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { doConfirm } = useConfirmGuide(tripId)

  const [travelDate, setTravelDate] = useState<string | null>(null)
  const [places, setPlaces] = useState<TripPlaceDetail[]>([])
  const [initialOrder, setInitialOrder] = useState<string[]>([])
  const [purposes, setPurposes] = useState<Record<string, PurposeTag[]>>({})
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [savingTimeId, setSavingTimeId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!tripId) return
    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const detail = await getTripDetail(tripId!)
        if (cancelled) return
        const ordered = sortPlacesForDisplay(detail.places)
        setTravelDate(detail.travelDate)
        setPlaces(ordered)
        setInitialOrder(ordered.map((place) => place.tripPlaceId))

        const entries = await Promise.all(
          ordered.map((place) =>
            getTripPlacePurpose(place.tripPlaceId)
              .then((res) => [place.tripPlaceId, res.purposeTags] as const)
              .catch(() => [place.tripPlaceId, []] as const),
          ),
        )
        if (cancelled) return
        setPurposes(Object.fromEntries(entries))
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

  const handleReorder = useCallback((fromIndex: number, toIndex: number) => {
    setPlaces((prev) => {
      const next = applyReorder(prev, fromIndex, toIndex)
      if (!isChronologicalVisitOrder(next)) return prev
      return withVisitOrder(next)
    })
  }, [])

  const handleSetVisitTime = useCallback(async (tripPlaceId: string, visitTime: string) => {
    setSavingTimeId(tripPlaceId)
    setError(null)
    try {
      await updateTripPlaceVisit(tripPlaceId, { visitTime })
      setPlaces((prev) =>
        withVisitOrder(
          sortPlacesForDisplay(
            prev.map((place) =>
              place.tripPlaceId === tripPlaceId ? { ...place, visitTime } : place,
            ),
          ),
        ),
      )
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setSavingTimeId(null)
    }
  }, [])

  const { dragIndex, pointerPos, gripProps, isDragging, isDropTarget } =
    useLongPressReorder(handleReorder)

  const dateParts = travelDate ? formatTimetableDate(travelDate) : null
  const draggedPlace = dragIndex !== null ? places[dragIndex] : null
  const orderChanged = useMemo(
    () =>
      places.length !== initialOrder.length ||
      places.some((place, index) => place.tripPlaceId !== initialOrder[index]),
    [places, initialOrder],
  )

  const onConfirm = async () => {
    if (!tripId) return
    setBusy(true)
    setError(null)
    try {
      if (orderChanged) {
        await reorderTripPlaces(
          tripId,
          places.map((place, index) => ({
            tripPlaceId: place.tripPlaceId,
            visitOrder: index + 1,
          })),
        )
        setInitialOrder(places.map((place) => place.tripPlaceId))
      }
      await doConfirm()
      setOpen(false)
      navigate(`/trips/${tripId}/guide`)
    } catch (e) {
      setError(toErrorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      <FlowHeader
        title="일정 확정"
        step={9}
        totalSteps={9}
        progress={1}
        onBack={() => navigate(-1)}
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

      {!loading && !loadError && (
        <div className="flex flex-1 flex-col overflow-y-auto px-5 pb-24 pt-4">
          {dateParts && (
            <div>
              <h2 className="text-[48px] font-extrabold leading-none tracking-[-1px] text-ink">
                {dateParts.monthLabel}
              </h2>
              <div className="mt-1 flex items-end gap-2">
                <p className="text-[40px] font-extrabold leading-none tracking-[-1.2px] text-ink">
                  {dateParts.dayPadded}
                </p>
                <p className="pb-1 text-[13px] font-medium italic text-ink-muted">
                  {dateParts.weekdayLabel}
                </p>
              </div>
            </div>
          )}

          {places.length === 0 ? (
            <p className="py-10 text-center text-[13px] text-ink-muted">
              등록된 장소가 없어요.
            </p>
          ) : (
            <>
              <p className="pb-1 pt-8 text-right text-[11px] font-medium text-ink-faint">
                ≡ 길게 눌러 순서 변경
              </p>
              <div className="border-t border-primary/35">
                {places.map((place, index) => {
                  const tags = purposes[place.tripPlaceId] ?? []
                  return (
                    <div
                      key={place.tripPlaceId}
                      data-row-index={index}
                      className={[
                        "flex items-center gap-2.5 border-b border-primary/35 py-2 transition-opacity",
                        isDragging(index) ? "opacity-40" : "",
                        isDropTarget(index) ? "bg-primary/10" : "",
                      ].join(" ")}
                    >
                      <Grip
                        size={16}
                        {...gripProps(index)}
                        className="shrink-0 cursor-grab text-ink-ghost"
                      />
                      {place.visitTime ? (
                        <span className="w-[52px] shrink-0 text-[14px] font-bold tabular-nums text-ink">
                          {formatVisitTime(place.visitTime)}
                        </span>
                      ) : (
                        <UnsetVisitTimeButton
                          disabled={savingTimeId === place.tripPlaceId}
                          onSelect={(time) => void handleSetVisitTime(place.tripPlaceId, time)}
                        />
                      )}
                      <span className="min-w-0 flex-1 truncate text-[15px] font-bold text-ink">
                        {place.name}
                      </span>
                      <div className="flex max-w-[42%] flex-wrap justify-end gap-1">
                        {tags.map((tag) => (
                          <span
                            key={tag.id}
                            className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-primary-foreground"
                          >
                            #{tag.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {error && <p className="pt-3 text-[13px] text-ink-soft">{error}</p>}
        </div>
      )}

      {!loading && !loadError && places.length > 0 && (
        <div className="absolute bottom-5 right-5 z-10">
          <button
            type="button"
            disabled={busy}
            onClick={() => setOpen(true)}
            className="h-10 rounded-[var(--radius-field)] bg-primary px-3.5 text-[13px] font-extrabold text-primary-foreground transition-[transform,filter,opacity] active:scale-[0.99] disabled:pointer-events-none disabled:opacity-45"
          >
            일정 확정하기
          </button>
        </div>
      )}

      {draggedPlace && pointerPos && (
        <div
          style={{
            position: "fixed",
            left: pointerPos.x,
            top: pointerPos.y,
            transform: "translate(-24px, -50%) rotate(-2deg)",
            pointerEvents: "none",
          }}
          className="z-40 flex w-[260px] items-center gap-2.5 rounded-[var(--radius-field)] border border-primary/40 bg-canvas px-3 py-3 shadow-[0_16px_32px_rgba(16,24,48,0.28)]"
        >
          <Grip size={16} className="shrink-0 text-ink-ghost" />
          <span className="w-[52px] shrink-0 text-[14px] font-bold tabular-nums text-ink-ghost">
            {formatVisitTime(draggedPlace.visitTime) || "--:--"}
          </span>
          <p className="truncate text-[15px] font-bold text-ink">{draggedPlace.name}</p>
        </div>
      )}

      <AlertDialog
        open={open}
        title="일정을 확정합니다"
        description="확정된 일정으로 가이드북이 생성됩니다."
        confirmLabel={busy ? "확정 중…" : "확정"}
        tone="success"
        onConfirm={() => void onConfirm()}
        onCancel={() => setOpen(false)}
      />
    </div>
  )
}
