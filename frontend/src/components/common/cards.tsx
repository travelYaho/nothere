/**
 * 카드 6종
 *  1) ScheduleCard      — 일정 목록 아이템 (번호 뱃지 + 제목 + 메타 + 진행중 강조)
 *  2) CongestionCard    — 혼잡 경고 카드 (빨강 테두리, 대안보기/유지)
 *  3) RecommendCard     — 추천 카드 (혼잡도 뱃지 포함)
 *  4) SearchResultItem  — 검색 결과 리스트 아이템 (+ 추가 버튼)
 *  5) BannerCard        — 홈 프로모션 배너 (그라디언트 + 이미지)
 *  6) ChangeLogItem     — 변경 기록 아이템 (BEFORE → AFTER)
 */
import { ArrowRight, Plus } from "./icons"
import { Button, CongestionBadge, type CongestionLevel } from "./primitives"

/* 1) ScheduleCard --------------------------------------------------- */
export function ScheduleCard({
  index,
  title,
  meta,
  active = false,
  onClick,
}: {
  index: number
  title: string
  meta: string
  active?: boolean
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={[
        "flex w-full items-center gap-3.5 rounded-[var(--radius-field)] bg-surface px-4 py-3.5 text-left",
        "shadow-[var(--shadow-card)] transition-transform active:scale-[0.99]",
        active ? "border-2 border-primary" : "border-[0.667px] border-transparent",
      ].join(" ")}
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] bg-primary text-[12px] font-extrabold text-white">
        {String(index).padStart(2, "0")}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[14px] font-bold tracking-[-0.28px] text-ink">
          {title}
        </span>
        <span className="mt-0.5 block text-[11px] font-medium text-ink-faint">{meta}</span>
      </span>
      <ArrowRight size={16} className="shrink-0 text-ink-faint" />
    </button>
  )
}

/* 2) CongestionCard ------------------------------------------------- */
export function CongestionCard({
  time,
  place,
  level,
  onAlternative,
  onKeep,
}: {
  time: string
  place: string
  level: CongestionLevel
  onAlternative?: () => void
  onKeep?: () => void
}) {
  const warn = level === "high"
  return (
    <div
      className={[
        "rounded-[var(--radius-field)] bg-surface px-4 py-3.5",
        warn
          ? "border-[0.667px] border-[#eeaaaa] /* shadow-[0_2px_5px_rgba(221,64,64,0.22)] */"
          : "border-[0.667px] border-transparent shadow-[var(--shadow-card)]",
      ].join(" ")}
    >
      <div className="flex items-center justify-between">
        <p className="text-[14px] font-bold text-ink">
          <span className="mr-2 text-[11px] font-semibold text-ink-faint">{time}</span>
          {place}
        </p>
        <CongestionBadge level={level} />
      </div>
      {warn && (
        <div className="flex gap-2 pt-3">
          <Button block onClick={onAlternative}>
            대안 보기
          </Button>
          <Button variant="ghost" onClick={onKeep} className="w-[68px] shrink-0 text-[15px] font-bold">
            유지
          </Button>
        </div>
      )}
    </div>
  )
}

/* 3) RecommendCard -------------------------------------------------- */
export function RecommendCard({
  tag,
  title,
  level,
  onClick,
}: {
  tag: string
  title: string
  level: CongestionLevel
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="w-full rounded-[var(--radius-field)] border-[0.667px] border-line-soft bg-surface p-4 text-left shadow-[var(--shadow-card)] transition-transform active:scale-[0.99]"
    >
      <p className="text-[9px] font-bold tracking-[0.9px] text-ink-faint">{tag}</p>
      <p className="mt-1 text-[15px] font-bold text-ink">{title}</p>
      <div className="mt-1.5">
        <CongestionBadge level={level} />
      </div>
    </button>
  )
}

/* 4) SearchResultItem ----------------------------------------------- */
export function SearchResultItem({
  name,
  category,
  added = false,
  onAdd,
}: {
  name: string
  category: string
  added?: boolean
  onAdd?: () => void
}) {
  return (
    <div className="flex items-center gap-3 rounded-[var(--radius-field)] bg-surface px-4 py-3 shadow-[var(--shadow-card)]">
      <span className="h-11 w-11 shrink-0 rounded-[12px] bg-surface-chip" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[14px] font-bold text-ink">{name}</span>
        <span className="block text-[11px] font-medium text-ink-faint">{category}</span>
      </span>
      <button
        onClick={onAdd}
        disabled={added}
        className={[
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors",
          added
            ? "bg-surface-chip text-ink-faint"
            : "bg-primary text-white hover:brightness-105 active:scale-95",
        ].join(" ")}
      >
        {added ? <span className="text-[11px] font-bold">완료</span> : <Plus size={16} />}
      </button>
    </div>
  )
}

/* 5) BannerCard ----------------------------------------------------- */
export function BannerCard({
  eyebrow,
  title,
  subtitle,
  tone = "primary",
  imageUrl,
  footer,
}: {
  eyebrow?: string
  title: React.ReactNode
  subtitle?: string
  tone?: "primary" | "warn"
  imageUrl?: string
  footer?: React.ReactNode
}) {
  const grad =
    tone === "warn"
      ? "linear-gradient(90deg, #dd874d 0%, rgba(218,145,97,0.64) 46%, rgba(218,145,97,0) 97%)"
      : "linear-gradient(90deg, #3A8F60 0%, rgba(58,143,96,0.64) 57%, rgba(34,92,60,0) 97%)"
  return (
    <div className="relative h-[210px] w-full overflow-hidden rounded-[var(--radius-banner)] bg-primary-strong">
      {imageUrl && (
        <img
          src={imageUrl}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}
      <div className="absolute inset-0" style={{ backgroundImage: grad }} />
      <div className="relative flex h-full flex-col p-[22px]">
        {eyebrow && (
          <p className="text-[11px] font-bold tracking-[0.88px] text-white/85">{eyebrow}</p>
        )}
        <div className="mt-1 text-[21px] font-extrabold leading-[26px] tracking-[-0.63px] text-white">
          {title}
        </div>
        {subtitle && (
          <p className="mt-2 text-[12px] leading-[18px] text-white/75">{subtitle}</p>
        )}
        {footer && <div className="mt-auto">{footer}</div>}
      </div>
    </div>
  )
}

/* 6) ChangeLogItem -------------------------------------------------- */
export function ChangeLogItem({
  from,
  fromLevel,
  to,
  toLevel,
}: {
  from: string
  fromLevel: CongestionLevel
  to: string
  toLevel: CongestionLevel
}) {
  return (
    <div className="flex items-center rounded-[var(--radius-field)] bg-surface px-4 py-3.5 shadow-[var(--shadow-card)]">
      <div className="min-w-0 flex-1">
        <p className="text-[9px] font-bold tracking-[0.9px] text-congestion-high">BEFORE</p>
        <p className="mt-0.5 truncate text-[13px] font-bold text-ink line-through decoration-ink-faint/60">
          {from}
        </p>
        <div className="mt-1">
          <CongestionBadge level={fromLevel} />
        </div>
      </div>
      <ArrowRight size={18} className="mx-3 shrink-0 text-ink-faint" />
      <div className="min-w-0 flex-1">
        <p className="text-[9px] font-bold tracking-[0.9px] text-congestion-low">AFTER</p>
        <p className="mt-0.5 truncate text-[13px] font-bold text-ink">{to}</p>
        <div className="mt-1">
          <CongestionBadge level={toLevel} />
        </div>
      </div>
    </div>
  )
}
