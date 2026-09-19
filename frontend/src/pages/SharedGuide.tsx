/**
 * 공유 링크 공개 가이드북 (비로그인)
 */
import { useEffect } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { ChangeLogItem } from "@/components/common/cards"
import { TimetableDateHeader } from "@/components/common/TimetableDateHeader"
import { BasicHeader } from "@/components/layout/navigation"
import { toUiCongestion, useConfirmGuide } from "@/features/recommendation"
import { formatVisitTime } from "@/features/trips/utils/placeOrder"

export default function SharedGuide() {
  const { token } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { guide, loading, error, loadPublic } = useConfirmGuide(undefined)

  useEffect(() => {
    if (token) void loadPublic(token)
  }, [token, loadPublic])

  // 카톡/문자 등으로 공유된 링크를 눌러 앱 히스토리 없이 바로 들어온 경우
  // navigate(-1)이 아무 반응도 안 해서(뒤로갈 곳이 없음) 다시 못 나가게 된다.
  // react-router는 이런 "직접 진입"에서 location.key를 "default"로 둔다.
  function handleBack() {
    if (location.key === "default") {
      navigate("/")
    } else {
      navigate(-1)
    }
  }

  return (
    <div className="relative flex flex-1 flex-col overflow-hidden font-guidebook">
      <BasicHeader title="공유 가이드북" onBack={handleBack} />
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
          </>
        )}
      </div>
    </div>
  )
}
