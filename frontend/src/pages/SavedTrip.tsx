/**
 * 확정 일정 저장본 — Figma「최종의 최종」(node 48:2244).
 * 최종 일정에서 저장하면 이 화면으로 오고, 일정 불러오기도 같은 경로를 쓴다.
 */
import { useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { SavedItineraryView, useConfirmGuide } from "@/features/recommendation"

export default function SavedTrip() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { guide, loading, error, loadGuide } = useConfirmGuide(tripId)

  useEffect(() => {
    void loadGuide()
  }, [loadGuide])

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
          onHome={() => navigate("/home")}
        />
      )}
    </div>
  )
}
