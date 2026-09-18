/**
 * 대안 찾기 2/2 — 원래 장소 vs 추천 대안 비교
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { Button } from "@/components/common/primitives"
import { AlertDialog, BottomSheet } from "@/components/feedback/modals"
import { FlowHeader } from "@/components/layout/navigation"
import { AlternativeCandidateCard } from "@/features/recommendation/components/AlternativeCandidateCard"
import { OriginalPlaceBar } from "@/features/recommendation/components/OriginalPlaceBar"
import {
  applyReplacement,
  keepTripPlace,
  toUiCongestion,
  useAccessToken,
  useCompareFlow,
} from "@/features/recommendation"
import type { CompareCandidate } from "@/features/recommendation"
import { kakaoMapSearchUrl } from "@/features/recommendation/utils/compareFormat"

export default function CompareAlternatives() {
  const { tripId, tripPlaceId } = useParams()
  const [params] = useSearchParams()
  const requestId = params.get("requestId") ?? undefined
  const navigate = useNavigate()
  const token = useAccessToken()
  const { data, loading, error, noCandidate, load } = useCompareFlow(requestId)

  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [keeping, setKeeping] = useState(false)
  const [keepError, setKeepError] = useState<string | null>(null)
  const [pending, setPending] = useState<CompareCandidate | null>(null)
  const [applying, setApplying] = useState(false)
  const [applyError, setApplyError] = useState<string | null>(null)
  const [detail, setDetail] = useState<CompareCandidate | null>(null)

  useEffect(() => {
    // load()의 identity는 requestId(또는 token)가 바뀔 때만 새로 생긴다 — 그 시점이
    // "이전 요청은 끝났고 새 요청을 시작한다"는 경계이므로, 이전 요청에서 골랐던 선택
    // 상태(교체 확인창·상세 보기)도 여기서 같이 정리한다. 안 그러면 요청이 전환된 뒤에도
    // 이전 후보를 가리키는 확인창이 열려 있을 수 있었다(2026-09-18, 코드 리뷰로 발견).
    // 주의: 이 효과는 requestId/token이 "바뀔 때"만 다시 돈다 — 같은 requestId로 다시
    // 불러오는 수동 재조회(예: 재시도 버튼)를 나중에 연결하면 이 reset은 안 실행된다.
    // 그런 경로를 추가할 때는 그 버튼 핸들러에서도 이 세 state를 직접 초기화해야 한다.
    // 지금은 그런 버튼이 없어 실제 문제는 아니고, handleApply()의 실행 직전 검증이
    // 어떤 경로로 재조회가 걸리든 잘못된 교체가 나가는 것 자체는 막아준다.
    setPending(null)
    setDetail(null)
    setApplyError(null)
    void load()
  }, [load])

  useEffect(() => {
    if (!data) return
    const first = data.candidates.find((c) => c.isEligible) ?? data.candidates[0]
    setExpandedId((prev) => {
      if (prev && data.candidates.some((c) => c.candidateId === prev)) return prev
      return first?.candidateId ?? null
    })
  }, [data])

  const visible = data?.candidates.filter((c) => c.isEligible) ?? []
  const originalLevel = toUiCongestion(data?.originalPlace.congestionLevel)

  const goRemaining = (reanalyze = false) => {
    navigate(`/trips/${tripId}/remaining`, reanalyze ? { state: { reanalyze: true } } : undefined)
  }

  const handleKeep = async () => {
    if (!tripPlaceId || keeping) return
    setKeeping(true)
    setKeepError(null)
    try {
      await keepTripPlace(tripPlaceId)
      goRemaining()
    } catch (e) {
      setKeepError(e instanceof Error ? e.message : "저장 실패")
    } finally {
      setKeeping(false)
    }
  }

  const handleApply = async () => {
    if (!tripPlaceId || !pending) return
    // pending은 확인창을 여는 시점의 후보 스냅샷이라, 그 뒤 재조회로 data가 바뀌었는데도
    // 확인창이 안 닫혔다면 더 이상 유효하지 않은 후보로 교체를 시도할 수 있다 — 실행
    // 직전에 "지금 화면이 보여주는 결과"에 실제로 속한 후보인지 전부 다시 확인한다
    // (2026-09-18, 코드 리뷰로 발견 — 후보 id만 확인하는 걸로는 부족하다는 지적 반영):
    // 로딩/오류/후보없음 상태가 아니고, 지금 결과가 이 화면의 requestId·tripPlaceId와
    // 실제로 일치하고, 그 후보가 지금도 적격(isEligible)인지까지 확인한다.
    const stillValid =
      !loading &&
      !error &&
      !noCandidate &&
      data != null &&
      data.requestId === requestId &&
      data.tripPlaceId === tripPlaceId &&
      data.candidates.some((c) => c.candidateId === pending.candidateId && c.isEligible)
    if (!stillValid) {
      setPending(null)
      setApplyError("대안 목록이 갱신되었어요. 다시 선택해 주세요.")
      return
    }
    setApplying(true)
    setApplyError(null)
    try {
      await applyReplacement(token, tripPlaceId, pending.candidateId)
      setPending(null)
      goRemaining(true)
    } catch (e) {
      setApplyError(e instanceof Error ? e.message : "교체 실패")
    } finally {
      setApplying(false)
    }
  }

  const openMap = (placeName: string) => {
    window.open(kakaoMapSearchUrl(placeName), "_blank", "noopener,noreferrer")
  }

  return (
    <div className="relative flex min-h-screen flex-1 flex-col">
      <FlowHeader
        title="대안 찾기"
        step={2}
        totalSteps={2}
        progress={1}
        onBack={() => navigate(-1)}
      />

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pb-4">
        {loading && <p className="pt-2 text-[13px] text-ink-muted">가까운 대안을 찾는 중…</p>}
        {error && <p className="pt-2 text-[13px] text-congestion-high">{error}</p>}
        {noCandidate && (
          <div className="pt-4">
            <p className="text-[13px] text-ink-muted">
              이 조건에 맞는 대안을 찾지 못했어요. 일정으로 돌아가 목적을 바꿔 다시 시도해
              주세요.
            </p>
            <div className="pt-3">
              <Button variant="ghost" block onClick={() => goRemaining()}>
                일정으로 돌아가기
              </Button>
            </div>
          </div>
        )}
        {!requestId && (
          <p className="pt-2 text-[13px] text-ink-muted">
            URL에 <code className="text-ink">?requestId=</code> 가 필요합니다.
          </p>
        )}
        {keepError && <p className="pt-2 text-[13px] text-congestion-high">{keepError}</p>}
        {applyError && <p className="pt-2 text-[13px] text-congestion-high">{applyError}</p>}

        {data && (
          <>
            <div className="pt-2">
              <OriginalPlaceBar
                name={data.originalPlace.name}
                level={originalLevel}
                keeping={keeping}
                onKeep={() => void handleKeep()}
              />
            </div>

            <div className="flex items-center justify-between px-1 pt-4">
              <p className="text-[14px] font-extrabold tracking-[-0.28px] text-ink">
                비슷한 경험의 가까운 대안{" "}
                <span className="text-primary">{visible.length}곳</span>
              </p>
              <p className="text-[11px] font-medium leading-[16.5px] text-ink-faint">추천순</p>
            </div>

            {visible.length === 0 && (
              <p className="pt-4 text-[13px] text-ink-muted">
                조건에 맞는 대안을 찾지 못했어요. 원래 일정을 유지할 수 있어요.
              </p>
            )}

            <div className="flex flex-col gap-2.5 pt-2">
              {visible.map((candidate, index) => {
                const hasDetail = Boolean(candidate.address || candidate.reasonText)
                return (
                  <AlternativeCandidateCard
                    key={candidate.candidateId}
                    candidate={candidate}
                    index={index}
                    expanded={candidate.candidateId === expandedId}
                    applying={applying && pending?.candidateId === candidate.candidateId}
                    onToggle={() =>
                      setExpandedId((prev) =>
                        prev === candidate.candidateId ? null : candidate.candidateId,
                      )
                    }
                    onChange={() => setPending(candidate)}
                    onMap={() => openMap(candidate.placeName)}
                    onDetail={hasDetail ? () => setDetail(candidate) : undefined}
                  />
                )
              })}
            </div>

            <p className="py-4 text-center text-[11px] leading-[16.5px] text-ink-ghost">
              예상 집중도는 방문 추이 기반 예측이며 실제와 다를 수 있습니다.
            </p>
          </>
        )}
      </div>

      <div className="shrink-0 border-t-[0.667px] border-line-soft bg-surface/95 px-4 pb-6 pt-3">
        <Button variant="ghost" block onClick={() => void handleKeep()} disabled={keeping}>
          {keeping ? "저장 중…" : "원래 일정 유지하기"}
        </Button>
      </div>

      <AlertDialog
        open={pending != null}
        title="장소를 교체할까요?"
        description={
          data && pending
            ? `${data.originalPlace.name} → ${pending.placeName} 으로 일정이 바뀝니다.`
            : undefined
        }
        confirmLabel={applying ? "적용 중…" : "교체하기"}
        onConfirm={() => void handleApply()}
        onCancel={() => {
          if (!applying) setPending(null)
        }}
      />

      <BottomSheet
        open={detail != null}
        title={detail?.placeName}
        onClose={() => setDetail(null)}
        footer={
          <Button variant="ghost" block onClick={() => setDetail(null)}>
            닫기
          </Button>
        }
      >
        {detail?.address && (
          <p className="text-[13px] leading-[19.5px] text-ink">{detail.address}</p>
        )}
        {detail?.reasonText && (
          <p className="mt-2 text-[13px] leading-[19.5px] text-ink-soft">{detail.reasonText}</p>
        )}
      </BottomSheet>
    </div>
  )
}
