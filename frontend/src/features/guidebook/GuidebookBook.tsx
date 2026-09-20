import { useCallback, useEffect, useRef, useState, type ReactNode, type PointerEvent } from "react"
import { ChevronLeft, ChevronRight } from "@/components/common/icons"
import type { GuideResponse } from "@/features/recommendation/types/part3"
import { GuideActionBar } from "./GuideActionBar"
import { GuideCoverPage } from "./GuideCoverPage"
import { GuideInnerPage } from "./GuideInnerPage"
import { GuidebookPrint } from "./GuidebookPrint"

const SWIPE_PX = 48
const FLIP_MS = 700
const FLIP_EASING = "cubic-bezier(0.22, 1, 0.36, 1)"

export function GuidebookBook({
  guide,
  memoReadOnly,
  onSaveMemo,
  onShare,
  onHome,
  shareBusy,
  boast,
}: {
  guide: GuideResponse
  memoReadOnly?: boolean
  onSaveMemo?: (content: string) => Promise<unknown>
  onShare: () => void
  onHome: () => void
  shareBusy?: boolean
  boast?: ReactNode
}) {
  const [page, setPage] = useState<0 | 1>(0)
  const [flipping, setFlipping] = useState(false)
  const dragStartX = useRef<number | null>(null)
  const pageRef = useRef(page)
  pageRef.current = page

  const goTo = useCallback((target: 0 | 1) => {
    if (pageRef.current === target) return
    setFlipping(true)
    setPage(target)
  }, [])

  useEffect(() => {
    if (!flipping) return
    const id = window.setTimeout(() => setFlipping(false), FLIP_MS + 80)
    return () => window.clearTimeout(id)
  }, [flipping, page])

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (fromInteractive(event.target)) return
    dragStartX.current = event.clientX
  }

  function onPointerUp(event: PointerEvent<HTMLDivElement>) {
    const start = dragStartX.current
    dragStartX.current = null
    if (start == null || fromInteractive(event.target)) return
    const delta = event.clientX - start
    if (delta <= -SWIPE_PX) goTo(1)
    else if (delta >= SWIPE_PX) goTo(0)
  }

  return (
    <div className="relative flex h-dvh min-h-0 flex-1 flex-col overflow-hidden bg-canvas font-guidebook">
      <div
        className="relative min-h-0 flex-1 overflow-hidden print:hidden"
        style={{ perspective: "1800px" }}
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
        onPointerCancel={() => {
          dragStartX.current = null
        }}
      >
        <div
          className="absolute inset-0 overflow-hidden bg-white"
          style={{
            zIndex: 1,
            pointerEvents: page === 1 && !flipping ? "auto" : "none",
          }}
        >
          <GuideInnerPage
            guide={guide}
            memoReadOnly={memoReadOnly}
            onSaveMemo={memoReadOnly ? undefined : onSaveMemo}
          />
        </div>

        <div
          data-testid="guidebook-cover-sheet"
          className="absolute inset-0 origin-left"
          style={{
            zIndex: 2,
            transformStyle: "preserve-3d",
            transform: page === 1 ? "rotateY(-180deg)" : "rotateY(0deg)",
            transition: `transform ${FLIP_MS}ms ${FLIP_EASING}`,
            pointerEvents: page === 0 ? "auto" : "none",
            willChange: "transform",
          }}
          onTransitionEnd={(event) => {
            if (event.propertyName === "transform") setFlipping(false)
          }}
        >
          <div
            className="absolute inset-0 overflow-hidden"
            style={{ backfaceVisibility: "hidden", WebkitBackfaceVisibility: "hidden" }}
          >
            <GuideCoverPage guide={guide} onOpenInner={() => goTo(1)} />
          </div>
        </div>

        {page === 1 ? (
          <button
            type="button"
            aria-label="표지로"
            disabled={flipping}
            onClick={() => goTo(0)}
            className="guidebook-nav absolute left-1 top-1/2 z-20 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-black/25 text-white/80 disabled:opacity-50"
          >
            <ChevronLeft size={22} />
          </button>
        ) : (
          <button
            type="button"
            aria-label="일정으로"
            disabled={flipping}
            onClick={() => goTo(1)}
            className="guidebook-nav absolute right-1 top-1/2 z-20 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-black/25 text-white/80 disabled:opacity-50"
          >
            <ChevronRight size={22} />
          </button>
        )}
      </div>

      {boast}

      <GuideActionBar
        onShare={onShare}
        onPrint={() => window.print()}
        onHome={onHome}
        shareBusy={shareBusy}
      />
      <GuidebookPrint guide={guide} memoReadOnly={memoReadOnly} />
    </div>
  )
}

function fromInteractive(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false
  return Boolean(target.closest("textarea, input, a, label, button"))
}
