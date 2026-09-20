/**
 * 공유 링크 공개 가이드북.
 * 둘러보기/좋아요에서 들어와도 홈 버튼은 로그인 홈(/home)으로 보낸다.
 */
import { useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { GuidebookBook } from "@/features/guidebook"
import { GUIDEBOOK_HOME_PATH } from "@/features/guidebook/GuideActionBar"
import { useConfirmGuide } from "@/features/recommendation"

export default function SharedGuide() {
  const { token } = useParams()
  const navigate = useNavigate()
  const { guide, loading, error, loadPublic } = useConfirmGuide(undefined)

  useEffect(() => {
    if (token) void loadPublic(token)
  }, [token, loadPublic])

  function handleHome() {
    navigate(GUIDEBOOK_HOME_PATH)
  }

  async function onShare() {
    await navigator.clipboard.writeText(window.location.href)
  }

  if (loading || !guide) {
    return (
      <div className="flex min-h-dvh flex-1 flex-col items-center justify-center gap-3 bg-canvas px-5 font-guidebook">
        {error ? (
          <>
            <p className="text-[13px] text-congestion-high">{error}</p>
            <button type="button" className="text-[14px] font-bold text-ink-soft" onClick={handleHome}>
              처음으로
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
        memoReadOnly
        onShare={() => void onShare()}
      />
    </div>
  )
}
