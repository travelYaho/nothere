/**
 * 확정 일정 저장본 — Figma「최종의 최종」(node 48:2244).
 * 최종 일정에서 저장하면 이 화면으로 오고, 일정 불러오기도 같은 경로를 쓴다.
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { AlertDialog } from "@/components/feedback/modals"
import { SavedItineraryView, useConfirmGuide } from "@/features/recommendation"
import { isGuidebookMade } from "@/features/recommendation/utils/guidebookMade"

export default function SavedTrip() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { guide, loading, error, loadGuide } = useConfirmGuide(tripId)
  const [alreadyOpen, setAlreadyOpen] = useState(false)

  useEffect(() => {
    void loadGuide()
  }, [loadGuide])

  function onMakeGuidebook() {
    if (!tripId) return
    const exists = Boolean(guide?.shareToken) || isGuidebookMade(tripId)
    if (exists) {
      setAlreadyOpen(true)
      return
    }
    navigate(`/trips/${tripId}/guide`)
  }

  return (
    <div className="relative flex min-h-dvh flex-1 flex-col overflow-hidden">
      {loading && (
        <div className="flex flex-1 items-center justify-center text-[13px] text-ink-muted">
          불러오는 중...
        </div>
      )}
      {!loading && error && (
        <div className="flex flex-1 items-center justify-center px-6 text-center text-[13px] font-medium text-ink-soft">
          {error}
        </div>
      )}
      {!loading && !error && guide && (
        <SavedItineraryView
          guide={guide}
          onBack={() => navigate(-1)}
          onEdit={() => tripId && navigate(`/trips/${tripId}/confirm`)}
          onMakeGuidebook={onMakeGuidebook}
          onHome={() => navigate("/home")}
        />
      )}
      <AlertDialog
        open={alreadyOpen}
        title="이미 만들어진 가이드북입니다"
        confirmLabel="보러 가기"
        cancelLabel="닫기"
        onConfirm={() => {
          setAlreadyOpen(false)
          if (tripId) navigate(`/trips/${tripId}/guide`)
        }}
        onCancel={() => setAlreadyOpen(false)}
      />
    </div>
  )
}
