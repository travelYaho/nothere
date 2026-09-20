/**
 * 확정 일정 가이드북 + 공유
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { GuidebookBook } from "@/features/guidebook"
import { useConfirmGuide } from "@/features/recommendation"
import { markGuidebookMade } from "@/features/recommendation/utils/guidebookMade"

export default function Guidebook() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { guide, loading, error, loadGuide, share, saveMemo } = useConfirmGuide(tripId)
  const [shareMsg, setShareMsg] = useState<string | null>(null)
  const [boastBusy, setBoastBusy] = useState(false)

  useEffect(() => {
    void loadGuide()
  }, [loadGuide])

  useEffect(() => {
    if (tripId && guide) markGuidebookMade(tripId)
  }, [tripId, guide])

  function handleHome() {
    navigate("/home")
  }

  const onShare = async () => {
    try {
      const res = await share()
      const url = res.absoluteUrl ?? `${window.location.origin}${res.url}`
      await navigator.clipboard.writeText(url)
      setShareMsg("공유 링크를 복사했습니다.")
    } catch (e) {
      setShareMsg(e instanceof Error ? e.message : "공유 실패")
    }
  }

  const onToggleBoast = async (checked: boolean) => {
    setBoastBusy(true)
    try {
      await share(checked ? "public" : "link")
      setShareMsg(checked ? "둘러보기에 공개했습니다." : "둘러보기에서 내렸습니다.")
    } catch (e) {
      setShareMsg(e instanceof Error ? e.message : "공개 설정 실패")
    } finally {
      setBoastBusy(false)
    }
  }

  if (loading || !guide) {
    return (
      <div className="flex min-h-dvh flex-1 flex-col items-center justify-center gap-3 bg-canvas px-5 font-guidebook">
        {error ? (
          <>
            <p className="text-[13px] text-congestion-high">{error}</p>
            <button type="button" className="text-[14px] font-bold text-ink-soft" onClick={handleHome}>
              홈으로
            </button>
          </>
        ) : (
          <p className="text-[13px] text-ink-muted">불러오는 중…</p>
        )}
      </div>
    )
  }

  return (
    <div className="flex h-dvh flex-1 flex-col overflow-hidden">
      <GuidebookBook
        guide={guide}
        onShare={() => void onShare()}
        onHome={handleHome}
        onSaveMemo={saveMemo}
        boast={
          <div className="border-t border-line-soft bg-white px-4 py-2 print:hidden">
            <label className="flex items-start gap-2.5 py-1">
              <input
                type="checkbox"
                checked={guide.visibility === "public"}
                disabled={boastBusy}
                onChange={(e) => void onToggleBoast(e.target.checked)}
                className="mt-1 h-4 w-4 accent-primary"
              />
              <span>
                <span className="block text-[14px] font-bold text-ink">자랑하기</span>
                <span className="mt-0.5 block text-[11px] text-ink-muted">둘러보기 목록에 공개</span>
              </span>
            </label>
            {shareMsg ? <p className="text-[12px] text-ink-muted">{shareMsg}</p> : null}
          </div>
        }
      />
    </div>
  )
}
