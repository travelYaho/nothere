/**
 * 기본 인터랙션 프리미티브 — Button, Chip, CongestionBadge.
 * 모든 상태(default/pressed/disabled/loading, selected 등)를 prop으로 제어.
 */
import type { ButtonHTMLAttributes, ReactNode } from "react"

/* ------------------------------------------------------------------ */
/* Button                                                              */
/* ------------------------------------------------------------------ */
type ButtonVariant = "primary" | "accent" | "ghost" | "text"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  loading?: boolean
  block?: boolean
  leadingIcon?: ReactNode
}

export function Button({
  variant = "primary",
  loading = false,
  block = false,
  leadingIcon,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading

  const variants: Record<ButtonVariant, string> = {
    primary:
      "bg-primary text-primary-foreground shadow-[var(--shadow-primary-soft)] hover:brightness-[1.05] active:brightness-95 active:scale-[0.99]",
    accent:
      "bg-[#1864F5] text-white shadow-[0px_8px_9px_rgba(24,100,245,0.55)] hover:brightness-[1.05] active:brightness-95 active:scale-[0.99]",
    ghost:
      "bg-surface text-ink-soft border-[0.667px] border-line-chip hover:bg-canvas active:scale-[0.99]",
    text: "bg-transparent text-primary hover:opacity-80 active:opacity-60",
  }

  const sizing =
    variant === "text"
      ? "h-auto px-1 py-0.5 text-[13px] font-bold"
      : "h-[54px] px-4 text-[16px] font-extrabold tracking-[-0.16px]"

  return (
    <button
      disabled={isDisabled}
      className={[
        "relative inline-flex items-center justify-center gap-2 rounded-[var(--radius-field)]",
        "transition-[transform,filter,opacity,background-color] duration-150 select-none",
        sizing,
        variants[variant],
        block ? "w-full" : "",
        isDisabled ? "opacity-45 pointer-events-none saturate-50" : "",
        className,
      ].join(" ")}
      {...props}
    >
      {loading && (
        <span className="absolute left-1/2 -translate-x-1/2 inline-block h-[18px] w-[18px] animate-spin rounded-full border-2 border-white/40 border-t-white" />
      )}
      <span
        className={[
          "inline-flex items-center gap-2",
          loading ? "opacity-0" : "",
        ].join(" ")}
      >
        {leadingIcon}
        {children}
      </span>
    </button>
  )
}

/* ------------------------------------------------------------------ */
/* Spinner                                                             */
/* ------------------------------------------------------------------ */
interface SpinnerProps {
  size?: number
  className?: string
}

/** 데이터 로딩 중임을 보여주는 회전 인디케이터. Button 내부 로딩 표시와 같은
 * 방식(테두리 일부만 색 채우고 animate-spin)을 밝은 배경용 색상으로 재사용한다.
 * Bookmarks.tsx의 "불러오는 중..." 텍스트를 대체했으므로, 스크린 리더에도 로딩
 * 상태가 전달되도록 role="status" + sr-only 텍스트를 같이 둔다. */
export function Spinner({ size = 24, className = "" }: SpinnerProps) {
  return (
    <span role="status">
      <span
        aria-hidden="true"
        className={[
          "inline-block animate-spin rounded-full border-2 border-line-chip border-t-primary",
          className,
        ].join(" ")}
        style={{ width: size, height: size }}
      />
      <span className="sr-only">불러오는 중...</span>
    </span>
  )
}

/* ------------------------------------------------------------------ */
/* Chip — single(단일선택) / multi(다중선택)                          */
/* ------------------------------------------------------------------ */
interface ChipProps {
  label: string
  selected?: boolean
  disabled?: boolean
  /** 시맨틱만 구분 — 스타일은 동일, 선택 규칙만 상위에서 다르게 처리 */
  variant?: "single" | "multi"
  onClick?: () => void
}

export function Chip({ label, selected = false, disabled = false, onClick }: ChipProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-pressed={selected}
      className={[
        "inline-flex h-[44px] items-center justify-center rounded-[var(--radius-pill)] px-4",
        "text-[13px] font-semibold transition-colors duration-150 border-[0.667px]",
        selected
          ? "bg-ink border-ink text-white"
          : "bg-surface border-line-chip text-ink-soft hover:border-ink/30",
        disabled ? "opacity-40 pointer-events-none" : "",
      ].join(" ")}
    >
      {label}
    </button>
  )
}

/* ------------------------------------------------------------------ */
/* CongestionBadge — 서비스 핵심 시맨틱                               */
/* ------------------------------------------------------------------ */
export type CongestionLevel = "high" | "medium" | "low" | "none"

const CONGESTION: Record<
  CongestionLevel,
  { label: string; color: string }
> = {
  high: { label: "혼잡 가능성 높음", color: "var(--color-congestion-high)" },
  medium: { label: "보통 예상", color: "var(--color-congestion-medium)" },
  low: { label: "여유 예상", color: "var(--color-congestion-low)" },
  none: { label: "예측 정보 없음", color: "var(--color-congestion-none)" },
}

export function CongestionBadge({
  level,
  label,
}: {
  level: CongestionLevel
  label?: string
}) {
  const c = CONGESTION[level]
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] font-semibold"
      style={{ color: c.color }}
    >
      <span
        style={{ background: c.color }}
        className="inline-block h-[7px] w-[7px] rounded-full"
      />
      {label ?? c.label}
    </span>
  )
}
