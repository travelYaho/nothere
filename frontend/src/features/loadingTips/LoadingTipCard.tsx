import { useEffect, useMemo, useRef, useState } from "react"
import { COMMON_TIPS, shuffledQueue, tipsForRegion, type LoadingTip } from "./tips"

const KIND_LABEL: Record<LoadingTip["kind"], string> = {
  quiz: "심심풀이 퀴즈",
  tip: "여행 팁",
  fact: "알고 계셨나요?",
}

/**
 * 대기 화면 보조 문구 — 실제 진행률과 무관하게 문구만 순환한다(진행 상황을 흉내 내지 않는다).
 * 문구 타이머는 조회 로직과 완전히 분리돼 있어서 요청을 다시 보내거나 결과에 영향을 주지 않는다.
 */
export function LoadingTipCard({
  regionName,
  intervalMs = 8000,
  revealHoldMs = 6000,
  slowAfterMs = 20000,
  random = Math.random,
}: {
  regionName?: string | null
  intervalMs?: number
  revealHoldMs?: number
  slowAfterMs?: number
  random?: () => number
}) {
  const pool = useMemo(() => [...tipsForRegion(regionName), ...COMMON_TIPS], [regionName])
  const queueRef = useRef<LoadingTip[]>([])
  const [current, setCurrent] = useState<LoadingTip>(() => {
    // 재시도로 카드가 다시 마운트될 때처럼 첫 렌더부터 지역을 알 수 있으니 처음 대기열도 지역 문구를 포함한다.
    const queue = shuffledQueue(pool, null, random)
    const first = queue.shift() as LoadingTip
    queueRef.current = queue
    return first
  })
  const [revealed, setRevealed] = useState(false)
  const [slow, setSlow] = useState(false)

  // 지역이 뒤늦게 확정되면 지금 보이는 문구는 그대로 두고 다음 순서부터 새 풀을 쓴다.
  // 마운트 직후에는 처음 만든 대기열을 그대로 써야 첫 한 바퀴에 같은 문구가 다시 나오지 않는다.
  const poolRef = useRef(pool)
  useEffect(() => {
    if (poolRef.current === pool) return
    poolRef.current = pool
    queueRef.current = []
  }, [pool])

  useEffect(() => {
    const id = setTimeout(() => setSlow(true), slowAfterMs)
    return () => clearTimeout(id)
  }, [slowAfterMs])

  useEffect(() => {
    const id = setTimeout(
      () => {
        if (queueRef.current.length === 0) {
          queueRef.current = shuffledQueue(pool, current, random)
        }
        setCurrent(queueRef.current.shift() as LoadingTip)
        setRevealed(false)
      },
      revealed ? revealHoldMs : intervalMs,
    )
    return () => clearTimeout(id)
  }, [current, revealed, pool, intervalMs, revealHoldMs, random])

  return (
    <div className="flex flex-col items-center gap-2 pt-8">
      {slow && (
        <p className="text-[12px] font-semibold leading-[18px] text-ink-muted">
          조회에 시간이 걸리고 있어요. 외부 정보 응답을 기다리는 중일 수 있어요.
        </p>
      )}
      <div className="min-h-[76px] max-w-[280px] rounded-[var(--radius-field)] bg-surface-chip px-4 py-3">
        <p className="text-[11px] font-bold text-primary">{KIND_LABEL[current.kind]}</p>
        <p className="pt-1 text-[13px] font-semibold leading-[20px] text-ink">{current.text}</p>
        {current.kind === "quiz" &&
          (revealed ? (
            <p className="pt-1 text-[13px] font-bold leading-[20px] text-primary">{current.answer}</p>
          ) : (
            <button
              type="button"
              onClick={() => setRevealed(true)}
              className="mt-1 text-[12px] font-semibold text-ink-muted underline"
            >
              정답 보기
            </button>
          ))}
      </div>
    </div>
  )
}
