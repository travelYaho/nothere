/**
 * Home — 홈(로그인) 화면.
 * Figma: 여기말GO / node 48:1966 "홈 (로그인)"
 */
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowRight, Bell, Heart, MapPin, Plus } from "@/components/common/icons"
import { Button, Spinner } from "@/components/common/primitives"
import { BannerCard, ScheduleCard } from "@/components/common/cards"
import { AlertDialog } from "@/components/feedback/modals"
import { BottomTab, useBottomTabNav } from "@/components/layout/navigation"
import { getHomeSummary } from "@/features/trips/api/tripsApi"
import { formatScheduleMeta } from "@/features/trips/utils/scheduleMeta"
import type { FeaturedGuide, ScheduleSummary } from "@/features/trips/types"
import { useLocationPermission } from "@/features/users/hooks/useLocationPermission"
import { useSession } from "@/store/sessionStore"
import { ApiError } from "@/types/api"
import brandMark from "@/assets/icons/logo.svg"

const FALLBACK_BANNER =
  "https://images.unsplash.com/photo-1543039625-14cbd3802e7d?w=680&h=420&fit=crop&auto=format"

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  return "일정을 불러오지 못했습니다."
}

export default function Home() {
  const navigate = useNavigate()
  const handleTabChange = useBottomTabNav()
  const { isLoading: sessionLoading } = useSession()
  const geo = useLocationPermission()

  const [draftSchedule, setDraftSchedule] = useState<ScheduleSummary | null>(null)
  const [recentSchedules, setRecentSchedules] = useState<ScheduleSummary[]>([])
  const [featuredGuide, setFeaturedGuide] = useState<FeaturedGuide | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (sessionLoading) return
    let cancelled = false
    setLoading(true)
    getHomeSummary()
      .then((res) => {
        if (cancelled) return
        setDraftSchedule(res.draftSchedule)
        setRecentSchedules(res.recentSchedules)
        setFeaturedGuide(res.featuredGuide)
      })
      .catch((err) => {
        if (!cancelled) setError(toErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [sessionLoading])

  return (
    <div className="relative flex flex-1 flex-col">
      <div className="flex items-center justify-between px-5 pb-3.5 pt-2">
        <h1 className="flex items-center gap-2 text-[24px] font-extrabold tracking-[-0.63px] text-ink">
          <img src={brandMark} alt="" className="h-8 w-auto" />
          여기말고
        </h1>
        <div className="flex items-center gap-3.5">
          <button
            type="button"
            aria-label="위치 권한 설정"
            onClick={geo.request}
            className="p-0.5"
          >
            <MapPin
              size={20}
              className={geo.state === "granted" ? "text-primary" : "text-ink-soft"}
            />
          </button>
          <Bell size={20} className="text-ink-soft" />
        </div>
      </div>

      <div className="px-4 pb-3.5">
        <BannerCard
          imageUrl={featuredGuide?.coverImageUrl || FALLBACK_BANNER}
          title={
            <>
              새로운 장소에서
              <br />
              새로운 기회를 찾아봐요
            </>
          }
          subtitle="여기말GO가 숨은 명소를 알려드릴게요. 함께 출발해볼까요?"
          footer={
            <button
              onClick={() =>
                navigate(featuredGuide ? `/guide/${featuredGuide.token}` : "/guides/explore")
              }
              className="-mx-[22px] -mb-[22px] flex h-[73px] w-[calc(100%+44px)] flex-col justify-center bg-black/20 px-[18px] text-left"
            >
              <p className="text-[9px] font-bold tracking-[0.9px] text-white/60">
                TODAY'S RECOMMENDATION
              </p>
              <p className="mt-[3px] truncate text-[13px] font-bold text-white">
                {featuredGuide ? featuredGuide.title : "가이드북 둘러보기"}
              </p>
              <p className="mt-[2px] text-[10px] font-semibold text-white/80">
                {featuredGuide
                  ? `${featuredGuide.regionName} · ♥ ${featuredGuide.likeCount}`
                  : "공개된 가이드북을 만나보세요"}
              </p>
            </button>
          }
        />
      </div>

      <div className="px-4 pb-2.5">
        <Button block leadingIcon={<Plus size={16} />} onClick={() => navigate("/trips/new")}>
          새 일정 점검하기
        </Button>
      </div>

      <div className="flex gap-2 px-4 pb-2.5">
        <button
          onClick={() => navigate("/guides/explore")}
          className="flex flex-1 items-center justify-between rounded-[var(--radius-field)] bg-surface px-4 py-3 text-left shadow-[var(--shadow-card)]"
        >
          <span className="text-[13px] font-bold text-ink">가이드북 둘러보기</span>
          <ArrowRight size={14} className="text-ink-faint" />
        </button>
        <button
          onClick={() => navigate("/guides/liked")}
          className="flex shrink-0 items-center gap-1.5 rounded-[var(--radius-field)] bg-surface px-4 py-3 shadow-[var(--shadow-card)]"
        >
          <Heart size={14} className="text-primary" />
          <span className="text-[13px] font-bold text-ink">좋아요함</span>
        </button>
      </div>

      {error && (
        <p className="px-4 pb-2 text-[12px] font-medium text-congestion-high">{error}</p>
      )}

      {loading && (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      )}

      {!loading && draftSchedule && (
        <div className="px-4 pb-2">
          <h2 className="text-[15px] font-extrabold tracking-[-0.3px] text-ink">이어서 점검하기</h2>
          <div className="mt-2.5">
            <ScheduleCard
              index={1}
              active
              title={draftSchedule.title}
              meta={formatScheduleMeta(draftSchedule)}
              onClick={() => navigate(draftSchedule.resumeUrl)}
            />
          </div>
        </div>
      )}

      <div className="flex-1 px-4 pb-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[15px] font-extrabold tracking-[-0.3px] text-ink">내 일정</h2>
          <button
            className="text-[11px] font-bold text-primary"
            onClick={() => navigate("/bookmarks")}
          >
            더보기
          </button>
        </div>
        <div className="mt-2.5 flex flex-col gap-2.5">
          {!loading && !error && recentSchedules.length === 0 && (
            <p className="py-6 text-center text-[13px] text-ink-muted">
              아직 등록된 일정이 없어요.
            </p>
          )}
          {recentSchedules.map((s, i) => (
            <ScheduleCard
              key={s.scheduleId}
              index={i + 2}
              title={s.title}
              meta={formatScheduleMeta(s)}
              onClick={() => navigate(s.resumeUrl)}
            />
          ))}
        </div>
      </div>

      <BottomTab active="home" onChange={handleTabChange} />

      <AlertDialog
        open={Boolean(geo.message)}
        title={
          geo.state === "granted"
            ? "위치 권한이 허용되었어요"
            : geo.state === "denied"
              ? "위치 권한을 허용해 주세요"
              : "위치를 확인할 수 없어요"
        }
        description={geo.state === "granted" ? undefined : (geo.message ?? undefined)}
        confirmLabel="확인"
        hideCancel
        onConfirm={geo.clearMessage}
        onCancel={geo.clearMessage}
      />
    </div>
  )
}
