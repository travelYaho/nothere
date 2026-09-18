/**
 * 헤더 & 네비게이션
 *  - StatusBar   : iOS 상태바 목업
 *  - BasicHeader : 뒤로가기 + 제목 (+ 우측 액션) — 홈/최종일정/상세
 *  - FlowHeader  : 뒤로가기 + 제목 + 스텝 + 진행바 — 온보딩 플로우
 *  - BottomTab   : 하단 탭 4개
 */
import { useNavigate } from "react-router-dom"
import { Bell, Bookmark, ChevronLeft, Home, MapPin, RouteIcon, User } from "../common/icons"


export function StatusBar() {
  return (
    <div className="flex items-center justify-between px-4 pb-1.5 pt-3.5">
      <span className="text-[13px] font-semibold text-ink">9:41</span>
      <div className="flex items-center gap-1.5 text-ink">
        <span className="text-[11px] font-bold tracking-tight">●●●</span>
        <span className="text-[12px] font-semibold">Wi-Fi</span>
        <span className="ml-0.5 inline-block h-3 w-6 rounded-[3px] border-[1.3px] border-ink/90 p-[1.5px]">
          <span className="block h-full w-[70%] rounded-[1px] bg-ink" />
        </span>
      </div>
    </div>
  )
}

export function BasicHeader({
  title,
  onBack,
  right,
}: {
  title: string
  onBack?: () => void
  right?: React.ReactNode
}) {
  return (
    <header className="flex items-center justify-between bg-canvas/95 px-5 py-2.5 backdrop-blur">
      <div className="flex items-center gap-2">
        {onBack !== undefined && (
          <button
            onClick={onBack}
            aria-label="뒤로가기"
            className="-ml-1 rounded-full p-1 text-ink hover:bg-ink/5"
          >
            <ChevronLeft size={22} />
          </button>
        )}
        <h1 className="text-[16px] font-extrabold tracking-[-0.32px] text-ink">{title}</h1>
      </div>
      {right}
    </header>
  )
}

export function FlowHeader({
  title,
  step,
  totalSteps,
  progress,
  onBack,
  subline,
}: {
  title: string
  step?: number
  totalSteps?: number
  progress: number // 0..1
  onBack?: () => void
  subline?: React.ReactNode
}) {
  return (
    <header className="bg-canvas/95 px-5 pb-3 pt-2 backdrop-blur">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {onBack !== undefined && (
            <button
              onClick={onBack}
              aria-label="뒤로가기"
              className="-ml-1 rounded-full p-1 text-ink hover:bg-ink/5"
            >
              <ChevronLeft size={22} />
            </button>
          )}
          <h1 className="text-[16px] font-extrabold tracking-[-0.32px] text-ink">{title}</h1>
        </div>
        {step !== undefined && totalSteps !== undefined && (
          <span className="text-[13px] font-semibold text-ink-faint">
            {step} / {totalSteps}
          </span>
        )}
      </div>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(progress * 100)}
        className="mt-2.5 h-[3px] w-full overflow-hidden rounded-full bg-[#dbe3f0]"
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-300"
          style={{ width: `${Math.round(progress * 100)}%` }}
        />
      </div>
      {subline && <div className="pt-1.5">{subline}</div>}
    </header>
  )
}

const TABS = [
  { key: "home", label: "홈", Icon: Home },
  { key: "create", label: "일정만들기", Icon: RouteIcon },
  { key: "saved", label: "보관함", Icon: Bookmark },
  { key: "my", label: "마이", Icon: User },
] as const

/** BottomTab 키 → 라우트. */
const TAB_ROUTES: Record<string, string> = {
  home: "/home",
  create: "/trips/new",
  saved: "/bookmarks",
  my: "/mypage",
}

/** BottomTab 클릭을 실제 라우팅으로 연결하는 공용 훅. */
export function useBottomTabNav() {
  const navigate = useNavigate()
  return function handleTabChange(key: string) {
    const path = TAB_ROUTES[key]
    if (path) navigate(path)
  }
}

export function BottomTab({
  active = "home",
  onChange,
}: {
  active?: string
  onChange?: (key: string) => void
}) {
  return (
    <nav className="sticky bottom-0 z-10 flex items-start border-t-[0.667px] border-line-soft bg-surface pb-5 pt-2">
      {TABS.map(({ key, label, Icon }) => {
        const on = key === active
        return (
          <button
            key={key}
            onClick={() => onChange?.(key)}
            className="flex flex-1 flex-col items-center gap-1"
          >
            <Icon size={22} className={on ? "text-primary" : "text-ink-faint"} />
            <span
              className={[
                "text-[10px] font-semibold tracking-[-0.1px]",
                on ? "text-primary" : "text-ink-faint",
              ].join(" ")}
            >
              {label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}

export { MapPin, Bell }
