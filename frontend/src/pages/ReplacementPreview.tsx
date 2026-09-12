/**
 * STEP8 — 교체 미리보기 및 승인
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { ChangeLogItem } from "@/components/common/cards"
import { Button } from "@/components/common/primitives"
import { AlertDialog } from "@/components/feedback/modals"
import { FlowHeader } from "@/components/layout/navigation"
import { toUiCongestion, usePreview } from "@/features/recommendation"

export default function ReplacementPreviewPage() {
  const { tripId, tripPlaceId } = useParams()
  const [params] = useSearchParams()
  const candidateId = params.get("candidateId") ?? undefined
  const navigate = useNavigate()
  const { data, loading, error, load, apply } = usePreview(tripPlaceId, candidateId)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [applying, setApplying] = useState(false)
  const [applyError, setApplyError] = useState<string | null>(null)

  useEffect(() => {
    void load()
  }, [load])

  const onConfirm = async () => {
    setApplying(true)
    setApplyError(null)
    try {
      await apply()
      setConfirmOpen(false)
      // 교체로 옛 분석이 지워졌으므로 결과 화면에서 재분석(POST)하도록 알려준다.
      navigate(`/trips/${tripId}/remaining`, { state: { reanalyze: true } })
    } catch (e) {
      setApplyError(e instanceof Error ? e.message : "교체 실패")
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="relative flex flex-1 flex-col">
      <FlowHeader
        title="교체 미리보기"
        step={8}
        totalSteps={9}
        progress={8 / 9}
        onBack={() => navigate(-1)}
      />
      <div className="flex flex-1 flex-col gap-4 px-5 pb-10 pt-2">
        {loading && <p className="text-[13px] text-ink-muted">미리보기 불러오는 중…</p>}
        {error && <p className="text-[13px] text-congestion-high">{error}</p>}
        {applyError && <p className="text-[13px] text-congestion-high">{applyError}</p>}

        {data && (
          <>
            <ChangeLogItem
              from={data.before.name}
              fromLevel={toUiCongestion(data.before.congestionLevel)}
              to={data.after.name}
              toLevel={toUiCongestion(data.after.congestionLevel)}
            />
            <div className="rounded-[var(--radius-field)] bg-surface px-4 py-3.5 shadow-[var(--shadow-card)]">
              <p className="text-[13px] font-semibold text-ink-soft">이동 시간 비교</p>
              <p className="mt-2 text-[14px] text-ink">
                기존 {data.totalTravelBefore}분 → 변경 후 {data.totalTravelAfter}분
                {data.extraMinutes != null && (
                  <span className="text-ink-muted"> (추가 {data.extraMinutes}분)</span>
                )}
              </p>
            </div>
            <Button block onClick={() => setConfirmOpen(true)}>
              이 장소로 교체
            </Button>
            <Button variant="ghost" block onClick={() => navigate(-1)}>
              다른 대안 보기
            </Button>
          </>
        )}
      </div>

      <AlertDialog
        open={confirmOpen}
        title="장소를 교체할까요?"
        description={
          data ? `${data.before.name} → ${data.after.name} 으로 일정이 바뀝니다.` : undefined
        }
        confirmLabel={applying ? "적용 중…" : "교체하기"}
        onConfirm={() => void onConfirm()}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  )
}
