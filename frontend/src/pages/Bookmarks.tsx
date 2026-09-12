/**
 * Bookmarks — "보관함" 화면. 확정/작성 중인 내 일정과, 내가 만든 가이드북을
 * 한 곳에 모아본다.
 * Figma: 여기말GO / node 132:2396 "보관함"
 *
 * 일정 목록은 "내 일정 전체 조회" API 가 아직 없어(홈 화면의 CONTINUE_SCHEDULE/
 * MY_SCHEDULES 도 같은 이유로 목업이다) 목업 데이터를 쓴다. X(삭제) 버튼도
 * 그래서 로컬 상태에서만 지운다 — 실제 여행 삭제(DELETE /trips/{id})는 하드
 * 삭제라 목업 id로 잘못 호출하면 안 되고, 목록 API가 생기면 그때 실 데이터 +
 * 실제 삭제로 교체하면 된다.
 *
 * "가이드북" 탭은 "좋아요한 가이드북"(GuideLiked 화면이 이미 따로 있음)이
 * 아니라 내가 공유해서 만든 가이드북 목록이다 — GET /guides/mine.
 */
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { GuidebookCard, ScheduleCard } from "@/components/common/cards"
import { BottomTab, useBottomTabNav } from "@/components/layout/navigation"
import { listMyGuides } from "@/features/guides/api/guidesApi"
import type { GuideCard } from "@/features/guides/types"
import { ApiError } from "@/types/api"

type TripStatus = "confirmed" | "draft"

interface SavedTrip {
  id: string
  title: string
  meta: string
  status: TripStatus
}

const INITIAL_TRIPS: SavedTrip[] = [
  { id: "1", title: "서울 서촌 당일치기", meta: "2026년 8월 14일 · 4곳 등록", status: "draft" },
  { id: "2", title: "전주 당일치기", meta: "2026년 8월 12일 · 4곳 등록 · 확정됨", status: "confirmed" },
  { id: "3", title: "경주 당일치기", meta: "2026년 8월 10일 · 4곳 등록 · 확정됨", status: "confirmed" },
]

const STATUS_FILTERS = [
  { key: "all", label: "전체" },
  { key: "confirmed", label: "확정" },
  { key: "draft", label: "작성 중" },
] as const
type StatusFilter = (typeof STATUS_FILTERS)[number]["key"]

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  return "가이드북을 불러오지 못했습니다."
}

export default function Bookmarks() {
  const navigate = useNavigate()
  const handleTabChange = useBottomTabNav()
  const [innerTab, setInnerTab] = useState<"trips" | "guidebooks">("trips")

  const [trips, setTrips] = useState(INITIAL_TRIPS)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")

  const [guides, setGuides] = useState<GuideCard[]>([])
  const [guidesLoaded, setGuidesLoaded] = useState(false)
  const [guidesLoading, setGuidesLoading] = useState(false)
  const [guidesError, setGuidesError] = useState<string | null>(null)

  useEffect(() => {
    if (innerTab !== "guidebooks" || guidesLoaded) return
    setGuidesLoading(true)
    listMyGuides(1)
      .then((res) => {
        setGuides(res.guides)
        setGuidesLoaded(true)
      })
      .catch((err) => setGuidesError(toErrorMessage(err)))
      .finally(() => setGuidesLoading(false))
  }, [innerTab, guidesLoaded])

  const filteredTrips = trips.filter((t) => statusFilter === "all" || t.status === statusFilter)

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
            {filteredTrips.length === 0 && (
              <p className="py-8 text-center text-[13px] text-ink-muted">
                해당하는 일정이 없어요.
              </p>
            )}
            {filteredTrips.map((trip, i) => (
              <ScheduleCard
                key={trip.id}
                index={i + 1}
                title={trip.title}
                meta={trip.meta}
                onRemove={() => setTrips((prev) => prev.filter((t) => t.id !== trip.id))}
              />
            ))}
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
                  key={guide.token}
                  title={guide.title}
                  regionName={guide.regionName}
                  placeCount={guide.placeCount}
                  tags={guide.tags}
                  authorNickname={guide.authorNickname}
                  coverImageUrl={guide.coverImageUrl}
                  likeCount={guide.likeCount}
                  isLikedByMe={guide.isLikedByMe}
                  onClick={() => navigate(`/guide/${guide.token}`)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      <BottomTab active="saved" onChange={handleTabChange} />
    </div>
  )
}
