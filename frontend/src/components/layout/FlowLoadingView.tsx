/**
 * 플로우 대기 화면 공통 레이아웃 — 일정 점검 / 대안 찾기 로딩이 같은 연출을 쓴다.
 */
import { Search } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { FlowHeader } from "@/components/layout/navigation"

export type FlowLoadingStep = {
  label: string
  progress: number
}

export function FlowLoadingView({
  headerTitle,
  headerProgress,
  title,
  steps,
  stepIndex,
  missingIdMessage,
  error,
  loading,
  onRetry,
  onBack,
}: {
  headerTitle: string
  headerProgress: number
  title: string
  steps: readonly FlowLoadingStep[]
  stepIndex: number
  missingIdMessage?: string
  error?: string | null
  loading: boolean
  onRetry?: () => void
  onBack?: () => void
}) {
  const step = steps[stepIndex] ?? steps[0]

  return (
    <div className="flex flex-1 flex-col">
      <FlowHeader title={headerTitle} progress={headerProgress} onBack={onBack} />

      <div className="flex flex-1 flex-col items-center justify-center px-8 text-center">
        <span className="flex size-16 items-center justify-center rounded-full bg-primary/10">
          <Search size={28} className="text-primary" />
        </span>
        <h2 className="pt-6 text-[17px] font-extrabold text-ink">{title}</h2>
        <p
          role="status"
          aria-live="polite"
          className="min-h-[21px] pt-1.5 text-[13px] font-semibold leading-[21px] text-ink-muted"
        >
          {step?.label}
        </p>
        <div className="w-60 pt-8">
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={step?.progress ?? 0}
            className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-chip"
          >
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-700 ease-out"
              style={{ width: `${step?.progress ?? 0}%` }}
            >
              <div className="absolute inset-y-0 left-0 w-1/3 animate-progress-shimmer rounded-full bg-white/40" />
            </div>
          </div>
          <p className="pt-2 text-[11px] font-semibold text-ink-faint">
            {stepIndex + 1} / {steps.length}
          </p>
        </div>
        {missingIdMessage && (
          <p className="pt-8 text-[12px] text-congestion-high">{missingIdMessage}</p>
        )}
        {error && !loading && (
          <div className="flex flex-col items-center gap-3 pt-8">
            <p role="alert" className="text-[13px] text-congestion-high">{error}</p>
            {onRetry && <Button onClick={onRetry}>다시 시도</Button>}
          </div>
        )}
      </div>
    </div>
  )
}
