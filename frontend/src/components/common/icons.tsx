/**
 * 아이콘 세트 — currentColor 기반이라 text-* 유틸로 색을 제어합니다.
 * 임포트된 디자인의 stroke 아이콘 스타일(round cap/join, 1.5~1.83 두께)을 따랐습니다.
 */
import type { SVGProps } from "react"

type IconProps = SVGProps<SVGSVGElement> & { size?: number }

function base({ size = 20, ...props }: IconProps) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    ...props,
  }
}

export const ChevronLeft = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M15 5l-7 7 7 7" />
  </svg>
)
export const ChevronRight = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M9 5l7 7-7 7" />
  </svg>
)
export const ChevronDown = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M6 9l6 6 6-6" />
  </svg>
)
export const ArrowRight = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
)
export const Plus = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M12 5v14M5 12h14" />
  </svg>
)
export const Close = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
)
export const Search = (p: IconProps) => (
  <svg {...base(p)}>
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" />
  </svg>
)
export const Calendar = (p: IconProps) => (
  <svg {...base(p)}>
    <rect x="3.5" y="5" width="17" height="16" rx="3" />
    <path d="M3.5 9.5h17M8 3v4M16 3v4" />
  </svg>
)
export const Bell = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M6 9a6 6 0 0112 0c0 5 2 6 2 6H4s2-1 2-6" />
    <path d="M10 20a2 2 0 004 0" />
  </svg>
)
export const MapPin = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M12 21s7-6.3 7-11a7 7 0 10-14 0c0 4.7 7 11 7 11z" />
    <circle cx="12" cy="10" r="2.5" />
  </svg>
)
export const Home = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M4 11l8-7 8 7" />
    <path d="M6 10v9h12v-9" />
  </svg>
)
export const RouteIcon = (p: IconProps) => (
  <svg {...base(p)}>
    <circle cx="6" cy="18" r="2.5" />
    <circle cx="18" cy="6" r="2.5" />
    <path d="M8.5 18H14a3 3 0 000-6h-4a3 3 0 010-6h5.5" />
  </svg>
)
export const Bookmark = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M6 4h12v16l-6-4-6 4z" />
  </svg>
)
export const User = (p: IconProps) => (
  <svg {...base(p)}>
    <circle cx="12" cy="8" r="3.5" />
    <path d="M5 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5" />
  </svg>
)
export const Grip = (p: IconProps) => (
  <svg {...base(p)} strokeWidth={2.4}>
    <path d="M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01" />
  </svg>
)
export const Doc = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M7 4.5h7l4 4V19.5a2 2 0 01-2 2H7a2 2 0 01-2-2v-13a2 2 0 012-2z" />
    <path d="M14 4.5V9h4.5" />
  </svg>
)
export const Share = (p: IconProps) => (
  <svg {...base({ size: 16, ...p })} viewBox="0 0 16 16" strokeWidth={1.5}>
    <path d="M8 2V10M11 5L8 2L5 5M3 9V12.5A1.5 1.5 0 004.5 14h7a1.5 1.5 0 001.5-1.5V9" />
  </svg>
)
export const Heart = ({
  size = 20,
  filled = false,
  className,
  ...props
}: IconProps & { filled?: boolean }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill={filled ? "currentColor" : "none"}
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    {...props}
  >
    <path d="M12 20.5s-7.2-4.4-9.8-9C.6 8 2 4.6 5.4 4.6c2 0 3.6 1.1 4.8 2.8 1.2-1.7 2.8-2.8 4.8-2.8 3.4 0 4.8 3.4 3.2 6.9-2.6 4.6-9.8 9-9.8 9z" />
  </svg>
)
export const Sliders = (p: IconProps) => (
  <svg {...base(p)}>
    <path d="M4 6h9M17 6h3M4 12h2M10 12h10M4 18h12M20 18h0.01" />
    <circle cx="13" cy="6" r="2" />
    <circle cx="6" cy="12" r="2" />
    <circle cx="16" cy="18" r="2" />
  </svg>
)
export const Dot = ({ size = 8, className }: { size?: number; className?: string }) => (
  <span
    className={className}
    style={{
      width: size,
      height: size,
      borderRadius: 999,
      background: "currentColor",
      display: "inline-block",
    }}
  />
)
