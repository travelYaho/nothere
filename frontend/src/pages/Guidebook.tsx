/**
 * 확정 일정 가이드북 + 공유
 */
import { useEffect, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { ChangeLogItem } from "@/components/common/cards"
import { TimetableDateHeader } from "@/components/common/TimetableDateHeader"
import { Button } from "@/components/common/primitives"
import { BasicHeader } from "@/components/layout/navigation"
import { toUiCongestion, useConfirmGuide } from "@/features/recommendation"
import { formatVisitTime } from "@/features/trips/utils/placeOrder"

export default function Guidebook() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { guide, loading, error, loadGuide, share } = useConfirmGuide(tripId)
  const [shareMsg, setShareMsg] = useState<string | null>(null)
  const [boastBusy, setBoastBusy] = useState(false)

  useEffect(() => {
    void loadGuide()
  }, [loadGuide])

  // 확정 직후(ConfirmTrip → 여기) 흐름뿐 아니라 보관함에서도 이 화면으로 들어온다.
  // 보관함에서 온 경우 "홈 화면" 만으로는 원래 있던 곳으로 못 돌아가서 뒤로가기도 둔다.
  // 히스토리 없이 직접 진입했으면(예: 링크로 바로 열림) -1이 아무 반응 없으니 홈으로 보낸다.
  function handleBack() {
    if (location.key === "default") {
      navigate("/home")
    } else {
      navigate(-1)
    }
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

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      <BasicHeader title="가이드북" onBack={handleBack} />
      <div className="flex flex-1 flex-col overflow-y-auto px-5 pb-10 pt-4">
        {loading && <p className="text-[13px] text-ink-muted">불러오는 중…</p>}
        {error && <p className="text-[13px] text-congestion-high">{error}</p>}

        {guide && (
          <>
            <TimetableDateHeader travelDate={guide.travelDate} />

            {guide.stops.length === 0 ? (
              <p className="py-10 text-center text-[13px] text-ink-muted">등록된 장소가 없어요.</p>
            ) : (
              <div className="mt-8 border-t border-primary/35">
                {guide.stops.map((stop) => (
                  <div key={`${stop.position}-${stop.placeName}`}>
                    <div className="flex items-center gap-2.5 border-b border-primary/35 py-1">
                      <span className="w-[52px] shrink-0 text-[14px] font-bold tabular-nums text-ink">
                        {formatVisitTime(stop.visitTime) || "--:--"}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-[15px] font-bold text-ink">
                        {stop.placeName}
                      </span>
                    </div>
                    {stop.wasReplaced && stop.replacedFrom && (
                      <div className="py-2">
                        <ChangeLogItem
                          from={stop.replacedFrom}
                          fromLevel={toUiCongestion("high")}
                          to={stop.placeName}
                          toLevel={toUiCongestion("low")}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="mt-8 flex flex-col gap-2">
              <label className="flex items-start gap-2.5 py-1">
                <input
                  type="checkbox"
                  checked={guide.visibility === "public"}
                  disabled={boastBusy}
                  onChange={(e) => void onToggleBoast(e.target.checked)}
                  className="mt-1 h-4 w-4 accent-primary"
                />
                <span>
                  <span className="block text-[15px] font-bold text-ink">자랑하기</span>
                  <span className="mt-0.5 block text-[12px] text-ink-muted">
                    둘러보기 목록에 공개
                  </span>
                </span>
              </label>
              <Button block onClick={() => void onShare()}>
                공유 링크 복사
              </Button>
              {shareMsg && <p className="text-[12px] text-ink-muted">{shareMsg}</p>}
            </div>
          </>
        )}

        {!loading && (
          <div className="mt-2">
            <Button variant="ghost" block onClick={() => navigate("/home")}>
              홈 화면
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
