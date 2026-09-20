/**
 * HomeGuest — 신규(비로그인) 홈 화면.
 * Figma: 여기말GO / node 48:2124 "신규 (비로그인)"
 */
import { Navigate, useNavigate } from "react-router-dom"
import { ArrowRight } from "@/components/common/icons"
import { Button, Spinner } from "@/components/common/primitives"
import { BannerCard } from "@/components/common/cards"
import { useSession } from "@/store/sessionStore"

const GUIDE_STEPS = [
  { no: "01", title: "가려던 일정을 등록한다", desc: "날짜 · 장소 · 동행 조건 입력" },
  { no: "02", title: "혼잡 예상 장소를 찾는다", desc: "집중률 API 기반 분석" },
  { no: "03", title: "가까운 대안으로 바꾼다", desc: "3km 이내 유사 경험 추천" },
] as const

function GuideStep({ no, title, desc }: { no: string; title: string; desc: string }) {
  return (
    <div className="flex w-full items-center gap-3.5 rounded-[var(--radius-field)] bg-surface px-4 py-3.5 shadow-[var(--shadow-card)]">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] bg-primary text-[12px] font-extrabold text-white">
        {no}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[14px] font-bold tracking-[-0.28px] text-ink">{title}</span>
        <span className="mt-0.5 block text-[11px] font-medium text-ink-faint">{desc}</span>
      </span>
    </div>
  )
}

export default function HomeGuest() {
  const navigate = useNavigate()
  const { session, isLoading } = useSession()

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner />
      </div>
    )
  }
  if (session) {
    return <Navigate to="/home" replace />
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="px-5 pb-3.5 pt-6">
        <h1 className="text-[24px] font-extrabold leading-[26px] tracking-[-0.5px] text-ink">
          이미 만든 여행 일정,
          <br />
          처음부터 다시 짜지 마세요
        </h1>
        <p className="mt-2 text-[14px] leading-[19.5px] tracking-[-0.63px] text-ink-soft">
          혼잡이 예상되는 곳 대신 새로운 곳을 추천해드릴게요.
        </p>
      </div>

      <div className="px-4 pb-3.5">
        <BannerCard
          tone="warn"
          imageUrl="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=680&h=420&fit=crop&auto=format"
          eyebrow={
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-[11px] font-bold tracking-[0.44px] text-white">
              <span className="h-[6px] w-[6px] rounded-[3px] bg-[#f03e3e]" />
              일정 혼잡 예상
            </span>
          }
          title="일정 점검이 필요해요"
          subtitle="현재 등록된 장소가 혼잡할 것으로 예상돼요. 매력 넘치는 다른 장소들을 추천해드릴게요."
          footer={
            <div className="-mx-[22px] -mb-[22px] flex h-[73px] bg-black/20">
              <div className="flex flex-1 flex-col justify-center px-[18px]">
                <p className="text-[9px] font-bold tracking-[0.9px] text-congestion-high">BEFORE</p>
                <p className="mt-[3px] text-[13px] font-bold text-white">경복궁 관람</p>
                <p className="mt-[2px] text-[10px] font-semibold text-congestion-high">
                  ● 주말 혼잡
                </p>
              </div>
              <div className="flex items-center px-[10px]">
                <ArrowRight size={13} className="text-white/70" />
              </div>
              <div className="flex flex-1 flex-col justify-center px-[18px]">
                <p className="text-[9px] font-bold tracking-[0.9px] text-congestion-low">AFTER</p>
                <p className="mt-[3px] text-[13px] font-bold text-white">창덕궁 후원</p>
                <p className="mt-[2px] text-[10px] font-semibold text-congestion-low">
                  ● 여유 예상
                </p>
              </div>
            </div>
          }
        />
      </div>

      <div className="flex flex-1 flex-col px-4 pb-6">
        <h2 className="text-[15px] font-extrabold tracking-[-0.3px] text-ink">이렇게 사용해요</h2>
        <div className="mt-2.5 flex flex-col gap-2">
          {GUIDE_STEPS.map((s) => (
            <GuideStep key={s.no} {...s} />
          ))}
        </div>
        <div className="mt-auto pt-6">
          <Button block onClick={() => navigate("/login")}>
            로그인 / 회원가입
          </Button>
        </div>
      </div>
    </div>
  )
}
