/**
 * 폼 입력 컴포넌트 — TextInput, PasswordInput, Select, TextArea, SearchBar, DatePicker.
 * 공통 상태: default / focus / filled / error / disabled.
 */
import { useMemo, useState, type InputHTMLAttributes } from "react"
import { Calendar, ChevronDown, ChevronLeft, ChevronRight, Search } from "./icons"

/* 공통 필드 래퍼 스타일 --------------------------------------------- */
function fieldClass(opts: {
  focused?: boolean
  error?: boolean
  disabled?: boolean
}) {
  return [
    "flex items-center gap-2.5 h-[52px] w-full rounded-[var(--radius-field)] px-4",
    "bg-surface text-[14px] transition-[border-color,box-shadow] duration-150",
    "border-[0.667px]",
    opts.error
      ? "border-congestion-high ring-2 ring-congestion-high/15"
      : opts.focused
        ? "border-primary ring-2 ring-primary/15"
        : "border-line",
    opts.disabled ? "bg-surface-sunken opacity-60 pointer-events-none" : "",
  ].join(" ")
}

export function FieldLabel({
  children,
  required,
  hint,
  right,
}: {
  children: React.ReactNode
  required?: boolean
  hint?: string
  right?: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between pb-2">
      <span className="text-[13px] font-semibold text-ink-soft">
        {children}
        {required && <span className="text-primary"> *</span>}
        {hint && <span className="ml-1.5 text-[11px] font-medium text-ink-faint">{hint}</span>}
      </span>
      {right}
    </div>
  )
}

function ErrorText({ text }: { text?: string }) {
  if (!text) return null
  return <p className="pt-1.5 text-[12px] font-medium text-congestion-high">{text}</p>
}

/* TextInput --------------------------------------------------------- */
interface TextInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  error?: string
}
export function TextInput({ error, disabled, className = "", ...props }: TextInputProps) {
  const [focused, setFocused] = useState(false)
  return (
    <div className={className}>
      <div className={fieldClass({ focused, error: !!error, disabled: !!disabled })}>
        <input
          {...props}
          disabled={disabled}
          onFocus={(e) => {
            setFocused(true)
            props.onFocus?.(e)
          }}
          onBlur={(e) => {
            setFocused(false)
            props.onBlur?.(e)
          }}
          className="w-full bg-transparent text-ink placeholder:text-ink-ghost outline-none"
        />
      </div>
      <ErrorText text={error} />
    </div>
  )
}

/* PasswordInput ----------------------------------------------------- */
export function PasswordInput({ error, disabled, ...props }: TextInputProps) {
  const [show, setShow] = useState(false)
  const [focused, setFocused] = useState(false)
  return (
    <div>
      <div className={fieldClass({ focused, error: !!error, disabled: !!disabled })}>
        <input
          {...props}
          type={show ? "text" : "password"}
          disabled={disabled}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className="w-full bg-transparent text-ink placeholder:text-ink-ghost outline-none"
        />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          className="shrink-0 text-[12px] font-semibold text-ink-faint hover:text-ink-soft"
        >
          {show ? "숨기기" : "보기"}
        </button>
      </div>
      <ErrorText text={error} />
    </div>
  )
}

/* Select ------------------------------------------------------------ */
export function Select({
  value,
  placeholder = "선택",
  options,
  disabled,
  onChange,
}: {
  value?: string
  placeholder?: string
  options: string[]
  disabled?: boolean
  onChange?: (v: string) => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className={fieldClass({ focused: open, disabled }) + " justify-between"}
      >
        <span className={value ? "text-ink" : "text-ink-ghost"}>
          {value ?? placeholder}
        </span>
        <ChevronDown size={16} className="text-ink-faint" />
      </button>
      {open && (
        <div className="absolute z-20 mt-2 w-full animate-pop-in rounded-[var(--radius-field)] border-[0.667px] border-line bg-surface p-1.5 /* shadow-[0_12px_24px_rgba(16,24,48,0.12)] */">
          {options.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => {
                onChange?.(opt)
                setOpen(false)
              }}
              className={[
                "flex w-full items-center rounded-[10px] px-3 py-2.5 text-[14px]",
                opt === value
                  ? "bg-primary/8 font-semibold text-primary"
                  : "text-ink-soft hover:bg-canvas",
              ].join(" ")}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/* TextArea ---------------------------------------------------------- */
export function TextArea({
  placeholder,
  disabled,
  rows = 3,
}: {
  placeholder?: string
  disabled?: boolean
  rows?: number
}) {
  const [focused, setFocused] = useState(false)
  return (
    <textarea
      rows={rows}
      placeholder={placeholder}
      disabled={disabled}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      className={[
        "w-full resize-none rounded-[var(--radius-field)] bg-surface px-4 py-3.5 text-[13px] leading-[19.5px]",
        "text-ink placeholder:text-ink-ghost outline-none border-[0.667px] transition-colors",
        focused ? "border-primary ring-2 ring-primary/15" : "border-line",
        disabled ? "bg-surface-sunken opacity-60" : "",
      ].join(" ")}
    />
  )
}

/* SearchBar --------------------------------------------------------- */
export function SearchBar({
  placeholder = "관광지 검색해서 추가",
}: {
  placeholder?: string
}) {
  const [focused, setFocused] = useState(false)
  return (
    <div className={fieldClass({ focused })}>
      <Search size={18} className="shrink-0 text-ink-faint" />
      <input
        placeholder={placeholder}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="w-full bg-transparent text-ink placeholder:text-ink-ghost outline-none"
      />
    </div>
  )
}

/* DatePicker -------------------------------------------------------- */
const WEEK = ["일", "월", "화", "수", "목", "금", "토"]

export function DatePicker({
  value,
  onChange,
}: {
  value?: Date
  onChange?: (d: Date) => void
}) {
  const [open, setOpen] = useState(false)
  const [view, setView] = useState(() => value ?? new Date(2026, 7, 1))
  const selected = value

  const grid = useMemo(() => {
    const first = new Date(view.getFullYear(), view.getMonth(), 1)
    const start = first.getDay()
    const days = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate()
    const cells: (Date | null)[] = []
    for (let i = 0; i < start; i++) cells.push(null)
    for (let d = 1; d <= days; d++)
      cells.push(new Date(view.getFullYear(), view.getMonth(), d))
    return cells
  }, [view])

  const fmt = (d?: Date) =>
    d
      ? `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(
          d.getDate(),
        ).padStart(2, "0")} (${WEEK[d.getDay()]})`
      : "날짜 선택"
  const same = (a: Date, b?: Date) =>
    b && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={fieldClass({ focused: open }) + " justify-between"}
      >
        <span className={selected ? "text-ink" : "text-ink-ghost"}>{fmt(selected)}</span>
        <Calendar size={18} className="text-ink-faint" />
      </button>

      {open && (
        <div className="absolute z-20 mt-2 w-[300px] animate-pop-in rounded-[var(--radius-banner)] border-[0.667px] border-line bg-surface p-4 /* shadow-[0_16px_36px_rgba(16,24,48,0.16)] */">
          <div className="flex items-center justify-between pb-3">
            <button
              type="button"
              onClick={() => setView(new Date(view.getFullYear(), view.getMonth() - 1, 1))}
              className="rounded-full p-1.5 text-ink-soft hover:bg-canvas"
            >
              <ChevronLeft size={18} />
            </button>
            <span className="text-[14px] font-bold text-ink">
              {view.getFullYear()}년 {view.getMonth() + 1}월
            </span>
            <button
              type="button"
              onClick={() => setView(new Date(view.getFullYear(), view.getMonth() + 1, 1))}
              className="rounded-full p-1.5 text-ink-soft hover:bg-canvas"
            >
              <ChevronRight size={18} />
            </button>
          </div>
          <div className="grid grid-cols-7 gap-y-1 text-center">
            {WEEK.map((w, i) => (
              <span
                key={w}
                className={[
                  "py-1 text-[11px] font-semibold",
                  i === 0 ? "text-congestion-high" : "text-ink-faint",
                ].join(" ")}
              >
                {w}
              </span>
            ))}
            {grid.map((d, i) => (
              <div key={i} className="flex justify-center py-0.5">
                {d && (
                  <button
                    type="button"
                    onClick={() => {
                      onChange?.(d)
                      setOpen(false)
                    }}
                    className={[
                      "flex h-9 w-9 items-center justify-center rounded-full text-[13px] transition-colors",
                      same(d, selected)
                        ? "bg-primary font-bold text-white"
                        : "text-ink-soft hover:bg-canvas",
                    ].join(" ")}
                  >
                    {d.getDate()}
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
