/**
 * StepHeader — 여행 생성 플로우(조건입력→장소등록→방문목적) 공통 상단 헤더.
 * Figma: 여기말GO / node 84:86 "FlowHeader"
 */
import { useNavigate } from "react-router-dom"
import { ChevronLeft } from "@/components/common/icons"

export function StepHeader({
  title,
  step,
  totalSteps,
  onBack,
}: {
  title: string
  step: number
  totalSteps: number
  onBack?: () => void
}) {
  const navigate = useNavigate()

  return (
    <div className="bg-canvas/95 flex w-full flex-col px-5 pb-2 pt-2">
      <div className="flex w-full items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={onBack ?? (() => navigate(-1))}
            className="-ml-1 rounded-full p-0.5 text-ink hover:bg-ink/5"
          >
            <ChevronLeft size={22} />
          </button>
          <h1 className="text-[16px] font-extrabold tracking-[-0.32px] text-ink">{title}</h1>
        </div>
        <span className="text-[13px] font-semibold text-ink-faint">
          {step} / {totalSteps}
        </span>
      </div>
      <div className="flex flex-col pt-2.5">
        <div className="h-[3px] w-full overflow-hidden rounded-full bg-surface-chip">
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-200"
            style={{ width: `${(step / totalSteps) * 100}%` }}
          />
        </div>
      </div>
    </div>
  )
}
