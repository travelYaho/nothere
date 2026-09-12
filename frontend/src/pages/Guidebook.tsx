/**
 * 확정 일정 가이드북 + 공유
 */
import { useEffect, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ChangeLogItem } from "@/components/common/cards"
import { TimetableDateHeader } from "@/components/common/TimetableDateHeader"
import { Button } from "@/components/common/primitives"
import { BasicHeader } from "@/components/layout/navigation"
import { toUiCongestion, useConfirmGuide } from "@/features/recommendation"
import { formatVisitTime } from "@/features/trips/utils/placeOrder"

export default function Guidebook() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const { guide, loading, error, loadGuide, share } = useConfirmGuide(tripId)
  const [shareMsg, setShareMsg] = useState<string | null>(null)

  useEffect(() => {
    void loadGuide()
  }, [loadGuide])

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

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden">
      <BasicHeader title="가이드북" />
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
