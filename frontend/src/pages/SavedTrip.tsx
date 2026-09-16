/**
 * 확정 일정 저장본 — Figma「최종의 최종」(node 48:2244).
 * 최종 일정에서 저장하면 이 화면으로 오고, 일정 불러오기도 같은 경로를 쓴다.
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { SavedItineraryView, useConfirmGuide } from "@/features/recommendation"

export default function SavedTrip() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { guide, loading, error, loadGuide, share } = useConfirmGuide(tripId)
  const [shareMsg, setShareMsg] = useState<string | null>(null)
  const [shareError, setShareError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    void loadGuide()
  }, [loadGuide])

  const onShare = async () => {
    setBusy(true)
    setShareError(null)
    setShareMsg(null)
    try {
      const res = await share()
      const url = res.absoluteUrl ?? `${window.location.origin}${res.url}`
      await navigator.clipboard.writeText(url)
      setShareMsg("공유 링크를 복사했습니다.")
    } catch (err) {
      setShareError(err instanceof Error ? err.message : "공유 실패")
    } finally {
      setBusy(false)
    }
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
          busy={busy}
          shareMsg={shareMsg}
          error={shareError}
          onBack={() => navigate(-1)}
          onShare={() => void onShare()}
          onPrint={() => window.print()}
        />
      )}
    </div>
  )
}
