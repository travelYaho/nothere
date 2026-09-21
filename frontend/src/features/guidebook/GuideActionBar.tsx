import { useNavigate } from "react-router-dom"
import { Share, Home, Doc } from "@/components/common/icons"

/** 가이드북 홈 버튼은 항상 로그인 홈으로 간다. 공개 가이드(`/guide/:token`)에서도 게스트 홈으로 보내지 않는다. */
export const GUIDEBOOK_HOME_PATH = "/home"

export function GuideActionBar({
  onShare,
  onPrint,
  shareBusy,
}: {
  onShare: () => void
  onPrint: () => void
  shareBusy?: boolean
}) {
  const navigate = useNavigate()

  return (
    <div className="guidebook-actions border-t border-line-soft bg-white/95 px-4 py-3 print:hidden">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onShare}
          disabled={shareBusy}
          className="flex h-[52px] min-w-0 flex-1 items-center justify-center gap-2 rounded-[16px] bg-[#219959] px-3 text-[15px] font-extrabold text-white disabled:opacity-45"
        >
          <Share size={16} />
          <span className="truncate">링크 복사 · 공유</span>
        </button>
        <button
          type="button"
          onClick={onPrint}
          className="flex h-[52px] w-[88px] shrink-0 items-center justify-center rounded-[16px] border border-line-chip bg-white px-2 text-[13px] font-bold text-ink-soft"
        >
          <span className="inline-flex items-center gap-1">
            <Doc size={14} />
            인쇄
          </span>
        </button>
        <button
          type="button"
          onClick={() => navigate(GUIDEBOOK_HOME_PATH)}
          aria-label="홈"
          className="flex size-[52px] shrink-0 items-center justify-center rounded-[16px] border border-line-chip bg-white text-ink-soft"
        >
          <Home size={20} />
        </button>
      </div>
    </div>
  )
}
