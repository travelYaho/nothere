/**
 * Home — 홈(로그인) 화면.
 * Figma: 여기말GO / node 48:1966 "홈 (로그인)"
 */
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ArrowRight, Bell, Heart, MapPin, Plus } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { BannerCard, ScheduleCard } from "@/components/common/cards"
import { BottomTab, useBottomTabNav } from "@/components/layout/navigation"
import { exploreGuides } from "@/features/guides/api/guidesApi"
import type { GuideCard } from "@/features/guides/types"
import { getHomeSummary } from "@/features/trips/api/tripsApi"
import { formatScheduleMeta } from "@/features/trips/utils/scheduleMeta"
import type { ScheduleSummary } from "@/features/trips/types"
import { ApiError } from "@/types/api"

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  return "일정을 불러오지 못했습니다."
}

export default function Home() {
  const navigate = useNavigate()
  const handleTabChange = useBottomTabNav()

  const [draftSchedule, setDraftSchedule] = useState<ScheduleSummary | null>(null)
  const [recentSchedules, setRecentSchedules] = useState<ScheduleSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  /** 공개 가이드북 중 좋아요가 가장 많은 것 — 배너를 누르면 이 가이드북으로 이동한다. */
  const [topGuide, setTopGuide] = useState<(GuideCard & { token: string }) | null>(null)

  useEffect(() => {
    let cancelled = false
    exploreGuides({ sort: "popular" })
      .then((res) => {
        if (cancelled) return
        const top = res.guides.find((g): g is GuideCard & { token: string } => !!g.token)
        setTopGuide(top ?? null)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    getHomeSummary()
      .then((res) => {
        if (cancelled) return
        setDraftSchedule(res.draftSchedule)
        setRecentSchedules(res.recentSchedules)
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
  }, [])

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between px-5 pb-3.5 pt-2">
        <h1 className="text-[24px] font-extrabold tracking-[-0.63px] text-ink">여기말고</h1>
        <div className="flex items-center gap-3.5">
          <MapPin size={20} className="text-ink-soft" />
          <Bell size={20} className="text-ink-soft" />
        </div>
      </div>

      <div className="px-4 pb-3.5">
        <BannerCard
          onClick={topGuide ? () => navigate(`/guide/${topGuide.token}`) : undefined}
          imageUrl={
            topGuide?.coverImageUrl ??
            "https://images.unsplash.com/photo-1543039625-14cbd3802e7d?w=680&h=420&fit=crop&auto=format"
          }
          title={
            <>
              새로운 장소에서
              <br />
              새로운 기회를 찾아봐요
            </>
          }
          subtitle="여기말GO가 숨은 명소를 알려드릴게요. 함께 출발해볼까요?"
          footer={
            topGuide && (
              <div className="-mx-[22px] -mb-[22px] flex h-[73px] items-center gap-3 bg-black/20 px-[18px]">
                <div className="min-w-0 flex-1">
                  <p className="text-[9px] font-bold tracking-[0.9px] text-white/60">
                    가장 인기 있는 가이드북
                  </p>
                  <p className="mt-[3px] truncate text-[13px] font-bold text-white">
                    {topGuide.regionName} · {topGuide.title}
                  </p>
                  <p className="mt-[2px] flex items-center gap-1 text-[10px] font-semibold text-white/80">
                    <Heart size={10} />
                    {topGuide.likeCount} · 장소 {topGuide.placeCount}곳
                  </p>
                </div>
                <ArrowRight size={16} className="shrink-0 text-white/80" />
              </div>
            )
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
    </div>
  )
}
