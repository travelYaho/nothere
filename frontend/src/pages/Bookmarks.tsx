/**
 * Bookmarks — "보관함" 화면. 확정/작성 중인 내 일정과, 내가 만든 가이드북을
 * 한 곳에 모아본다.
 * Figma: 여기말GO / node 132:2396 "보관함"
 *
 * "일정" 탭은 GET /trips(상태 필터+페이지네이션)를, X(삭제) 버튼은 실제
 * DELETE /trips/{id}를 쓴다 — 하드 삭제라 실패하면 목록을 원래대로 되돌린다.
 *
 * "가이드북" 탭은 "좋아요한 가이드북"(GuideLiked 화면이 이미 따로 있음)이
 * 아니라 내가 공유해서 만든 가이드북 목록이다 — GET /guides/mine.
 */
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { GuidebookCard, ScheduleCard } from "@/components/common/cards"
import { Button } from "@/components/common/primitives"
import { BottomTab, useBottomTabNav } from "@/components/layout/navigation"
import { listMyGuides } from "@/features/guides/api/guidesApi"
import type { GuideCard } from "@/features/guides/types"
import { deleteTrip, listTrips } from "@/features/trips/api/tripsApi"
import { formatScheduleMeta } from "@/features/trips/utils/scheduleMeta"
import type { TripSummary } from "@/features/trips/types"
import { ApiError } from "@/types/api"

const STATUS_FILTERS = [
  { key: "all", label: "전체" },
  { key: "confirmed", label: "확정" },
  { key: "draft", label: "작성 중" },
] as const
type StatusFilter = (typeof STATUS_FILTERS)[number]["key"]

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  return "불러오지 못했습니다."
}

export default function Bookmarks() {
  const navigate = useNavigate()
  const handleTabChange = useBottomTabNav()
  const [innerTab, setInnerTab] = useState<"trips" | "guidebooks">("trips")

  const [trips, setTrips] = useState<TripSummary[]>([])
  const [tripsPage, setTripsPage] = useState(1)
  const [tripsHasNext, setTripsHasNext] = useState(false)
  const [tripsLoading, setTripsLoading] = useState(false)
  const [tripsLoadingMore, setTripsLoadingMore] = useState(false)
  const [tripsError, setTripsError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")

  useEffect(() => {
    if (innerTab !== "trips") return
    let cancelled = false
    setTripsLoading(true)
    setTripsError(null)
    listTrips({ status: statusFilter === "all" ? undefined : statusFilter, page: 1 })
      .then((res) => {
        if (cancelled) return
        setTrips(res.trips)
        setTripsPage(1)
        setTripsHasNext(res.hasNext)
      })
      .catch((err) => {
        if (cancelled) return
        setTripsError(toErrorMessage(err))
      })
      .finally(() => {
        if (cancelled) return
        setTripsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [innerTab, statusFilter])

  async function loadMoreTrips() {
    setTripsLoadingMore(true)
    try {
      const res = await listTrips({
        status: statusFilter === "all" ? undefined : statusFilter,
        page: tripsPage + 1,
      })
      setTrips((prev) => [...prev, ...res.trips])
      setTripsHasNext(res.hasNext)
      setTripsPage((p) => p + 1)
    } catch (err) {
      setTripsError(toErrorMessage(err))
    } finally {
      setTripsLoadingMore(false)
    }
  }

  async function handleRemoveTrip(tripId: string) {
    const previous = trips
    setTrips((prev) => prev.filter((t) => t.tripId !== tripId))
    try {
      await deleteTrip(tripId)
    } catch (err) {
      setTrips(previous)
      setTripsError(toErrorMessage(err))
    }
  }

  const [guides, setGuides] = useState<GuideCard[]>([])
  const [guidesPage, setGuidesPage] = useState(1)
  const [guidesHasNext, setGuidesHasNext] = useState(false)
  const [guidesLoaded, setGuidesLoaded] = useState(false)
  const [guidesLoading, setGuidesLoading] = useState(false)
  const [guidesLoadingMore, setGuidesLoadingMore] = useState(false)
  const [guidesError, setGuidesError] = useState<string | null>(null)

  useEffect(() => {
    if (innerTab !== "guidebooks" || guidesLoaded) return
    setGuidesLoading(true)
    setGuidesError(null)
    listMyGuides(1)
      .then((res) => {
        setGuides(res.guides)
        setGuidesPage(1)
        setGuidesHasNext(res.hasNext)
        setGuidesLoaded(true)
      })
      .catch((err) => setGuidesError(toErrorMessage(err)))
      .finally(() => setGuidesLoading(false))
  }, [innerTab, guidesLoaded])

  async function loadMoreGuides() {
    setGuidesLoadingMore(true)
    try {
      const res = await listMyGuides(guidesPage + 1)
      setGuides((prev) => [...prev, ...res.guides])
      setGuidesHasNext(res.hasNext)
      setGuidesPage((p) => p + 1)
    } catch (err) {
      setGuidesError(toErrorMessage(err))
    } finally {
      setGuidesLoadingMore(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="px-5 pb-2.5 pt-2">
        <h1 className="text-[16px] font-extrabold tracking-[-0.32px] text-ink">보관함</h1>
        <p className="pt-0.5 text-[11px] font-medium text-ink-faint">
          확정한 일정과 가이드북을 모아봐요
        </p>
      </div>

      <div className="flex border-b-[0.667px] border-line-soft px-5">
        {(["trips", "guidebooks"] as const).map((key) => (
          <button
            key={key}
            onClick={() => setInnerTab(key)}
            className="relative flex-1 pb-2.5 pt-1 text-center"
          >
            <span
              className={[
                "text-[13px] font-bold",
                innerTab === key ? "text-ink" : "text-ink-faint",
              ].join(" ")}
            >
              {key === "trips" ? "일정" : "가이드북"}
            </span>
            {innerTab === key && (
              <span className="absolute inset-x-0 -bottom-px h-[2px] rounded-full bg-primary" />
            )}
          </button>
        ))}
      </div>

      {innerTab === "trips" && (
        <div className="flex flex-1 flex-col overflow-y-auto px-5">
          <div className="flex gap-2 pb-2 pt-3">
            {STATUS_FILTERS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setStatusFilter(key)}
                className={[
                  "rounded-[var(--radius-pill)] px-3.5 py-1.5 text-[12px] font-bold transition-colors",
                  statusFilter === key
                    ? "bg-ink text-white"
                    : "border-[0.667px] border-line-chip bg-surface text-ink-soft",
                ].join(" ")}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-2.5 pb-4 pt-1">
            {tripsLoading && (
              <p className="py-8 text-center text-[13px] text-ink-muted">불러오는 중...</p>
            )}
            {!tripsLoading && tripsError && (
              <p className="py-8 text-center text-[13px] font-medium text-congestion-high">
                {tripsError}
              </p>
            )}
            {!tripsLoading && !tripsError && trips.length === 0 && (
              <p className="py-8 text-center text-[13px] text-ink-muted">
                해당하는 일정이 없어요.
              </p>
            )}
            {!tripsLoading &&
              !tripsError &&
              trips.map((trip, i) => (
                <ScheduleCard
                  key={trip.tripId}
                  index={i + 1}
                  title={trip.title}
                  meta={formatScheduleMeta(trip)}
                  onClick={() => navigate(trip.resumeUrl)}
                  onRemove={() => void handleRemoveTrip(trip.tripId)}
                />
              ))}
            {!tripsLoading && !tripsError && tripsHasNext && (
              <Button
                variant="ghost"
                block
                loading={tripsLoadingMore}
                onClick={() => void loadMoreTrips()}
              >
                더보기
              </Button>
            )}
          </div>
        </div>
      )}

      {innerTab === "guidebooks" && (
        <div className="flex flex-1 flex-col overflow-y-auto px-5 pt-3">
          {guidesLoading && <p className="py-8 text-center text-[13px] text-ink-muted">불러오는 중...</p>}
          {!guidesLoading && guidesError && (
            <p className="py-8 text-center text-[13px] font-medium text-congestion-high">{guidesError}</p>
          )}
          {!guidesLoading && !guidesError && guides.length === 0 && (
            <p className="py-8 text-center text-[13px] text-ink-muted">
              아직 만든 가이드북이 없어요.
            </p>
          )}
          {!guidesLoading && !guidesError && guides.length > 0 && (
            <div className="flex flex-col gap-2.5 pb-4">
              {guides.map((guide) => (
                <GuidebookCard
                  key={guide.tripId}
                  title={guide.title}
                  regionName={guide.regionName}
                  placeCount={guide.placeCount}
                  tags={guide.tags}
                  authorNickname={guide.authorNickname}
                  coverImageUrl={guide.coverImageUrl}
                  likeCount={guide.likeCount}
                  isLikedByMe={guide.isLikedByMe}
                  onClick={() => navigate(`/trips/${guide.tripId}/guide`)}
                />
              ))}
            </div>
          )}
          {!guidesLoading && !guidesError && guidesHasNext && (
            <div className="pb-4">
              <Button variant="ghost" block loading={guidesLoadingMore} onClick={() => void loadMoreGuides()}>
                더보기
              </Button>
            </div>
          )}
        </div>
      )}

      <BottomTab active="saved" onChange={handleTabChange} />
    </div>
  )
}
