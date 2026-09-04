/**
 * STEP9 — 최종 일정 확정
 */
import { useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Button } from "@/components/common/primitives"
import { AlertDialog } from "@/components/feedback/modals"
import { FlowHeader } from "@/components/layout/navigation"
import { useConfirmGuide } from "@/features/recommendation"

export default function ConfirmTrip() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { doConfirm } = useConfirmGuide(tripId)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onConfirm = async () => {
    setBusy(true)
    setError(null)
    try {
      await doConfirm()
      setOpen(false)
      navigate(`/trips/${tripId}/guide`)
    } catch (e) {
      setError(e instanceof Error ? e.message : "확정 실패")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex flex-1 flex-col">
      <FlowHeader
        title="일정 확정"
        step={9}
        totalSteps={9}
        progress={1}
        onBack={() => navigate(-1)}
      />
      <div className="flex flex-1 flex-col gap-4 px-5 pb-10 pt-6">
        <h2 className="text-[20px] font-extrabold tracking-[-0.4px] text-ink">
          이 일정으로 확정할까요?
        </h2>
        <p className="text-[13px] leading-[19.5px] text-ink-soft">
          확정 후에는 가이드북을 만들고 링크로 공유할 수 있습니다. 남은 혼잡 장소가 있으면
          확정할 수 없습니다.
        </p>
        {error && <p className="text-[13px] text-congestion-high">{error}</p>}
        <Button block onClick={() => setOpen(true)}>
          일정 확정하기
        </Button>
        <Button variant="ghost" block onClick={() => navigate(`/trips/${tripId}/remaining`)}>
          남은 혼잡 다시 보기
        </Button>
      </div>

      <AlertDialog
        open={open}
        title="일정을 확정합니다"
        description="확정된 일정으로 가이드북이 생성됩니다."
        confirmLabel={busy ? "확정 중…" : "확정"}
        tone="success"
        onConfirm={() => void onConfirm()}
        onCancel={() => setOpen(false)}
      />
    </div>
  )
}
