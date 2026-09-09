/**
 * Home — 홈(로그인) 화면.
 * Figma: 여기말GO / node 48:1966 "홈 (로그인)"
 */
import { useNavigate } from "react-router-dom"
import { ArrowRight, Bell, Heart, MapPin, Plus } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { BannerCard, ScheduleCard } from "@/components/common/cards"
import { BottomTab, useBottomTabNav } from "@/components/layout/navigation"

const CONTINUE_SCHEDULE = { title: "서울 서촌 당일치기", meta: "2026년 8월 14일 | 4곳 등록" }
const MY_SCHEDULES = [
  { title: "전주 당일치기", meta: "2026년 8월 12일 | 4곳 등록" },
  { title: "경주 당일치기", meta: "2026년 8월 10일 | 4곳 등록" },
]

export default function Home() {
  const navigate = useNavigate()
  const handleTabChange = useBottomTabNav()

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
          imageUrl="https://images.unsplash.com/photo-1543039625-14cbd3802e7d?w=680&h=420&fit=crop&auto=format"
          title={
            <>
              새로운 장소에서
              <br />
              새로운 기회를 찾아봐요
            </>
          }
          subtitle="여기말GO가 숨은 명소를 알려드릴게요. 함께 출발해볼까요?"
          footer={
            <div className="-mx-[22px] -mb-[22px] flex h-[73px] flex-col justify-center bg-black/20 px-[18px]">
              <p className="text-[9px] font-bold tracking-[0.9px] text-white/60">
                TODAY'S RECOMMENDATION
              </p>
              <p className="mt-[3px] text-[13px] font-bold text-white">유성온천</p>
              <p className="mt-[2px] text-[10px] font-semibold text-congestion-low">● 여유 예상</p>
            </div>
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

      <div className="px-4 pb-2">
        <h2 className="text-[15px] font-extrabold tracking-[-0.3px] text-ink">이어서 점검하기</h2>
        <div className="mt-2.5">
          <ScheduleCard index={1} active {...CONTINUE_SCHEDULE} />
        </div>
      </div>

      <div className="flex-1 px-4 pb-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[15px] font-extrabold tracking-[-0.3px] text-ink">내 일정</h2>
          <button className="text-[11px] font-bold text-primary">더보기</button>
        </div>
        <div className="mt-2.5 flex flex-col gap-2.5">
          {MY_SCHEDULES.map((s, i) => (
            <ScheduleCard key={s.title} index={i + 2} {...s} />
          ))}
        </div>
      </div>

      <BottomTab active="home" onChange={handleTabChange} />
    </div>
  )
}
