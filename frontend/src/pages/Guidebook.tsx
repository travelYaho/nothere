/**
 * 확정 일정 가이드북 + 공유
 */
import { useEffect, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { ChangeLogItem, ScheduleCard } from "@/components/common/cards"
import { Button } from "@/components/common/primitives"
import { BasicHeader } from "@/components/layout/navigation"
import { toUiCongestion, useConfirmGuide } from "@/features/recommendation"

export default function Guidebook() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { guide, loading, error, loadGuide, share } = useConfirmGuide(tripId)
  const [shareMsg, setShareMsg] = useState<string | null>(null)

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

  return (
    <div className="relative flex flex-1 flex-col">
      <BasicHeader title="가이드북" onBack={handleBack} />
      <div className="flex flex-1 flex-col gap-4 px-5 pb-10 pt-2">
        {loading && <p className="text-[13px] text-ink-muted">불러오는 중…</p>}
        {error && <p className="text-[13px] text-congestion-high">{error}</p>}

        {guide && (
          <>
            <div>
              <h2 className="text-[18px] font-extrabold text-ink">{guide.title}</h2>
              {guide.travelDate && (
                <p className="mt-1 text-[12px] text-ink-muted">{guide.travelDate}</p>
              )}
            </div>

            <div className="flex flex-col gap-2.5">
              {guide.stops.map((stop) => (
                <div key={`${stop.position}-${stop.placeName}`} className="flex flex-col gap-2">
                  <ScheduleCard
                    index={stop.position}
                    title={stop.placeName}
                    meta={[
                      stop.visitTime ? `${stop.visitTime}` : null,
                      stop.travelToNext
                        ? `다음까지 ${stop.travelToNext.durationMin}분 · ${stop.travelToNext.distanceM}m`
                        : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  />
                  {stop.wasReplaced && stop.replacedFrom && (
                    <ChangeLogItem
                      from={stop.replacedFrom}
                      fromLevel={toUiCongestion("high")}
                      to={stop.placeName}
                      toLevel={toUiCongestion("low")}
                    />
                  )}
                </div>
              ))}
            </div>

            <Button block onClick={() => void onShare()}>
              공유 링크 복사
            </Button>
            {shareMsg && <p className="text-[12px] text-ink-muted">{shareMsg}</p>}
          </>
        )}

        {!loading && (
          <Button variant="ghost" block onClick={() => navigate("/home")}>
            홈 화면
          </Button>
        )}
      </div>
    </div>
  )
}
