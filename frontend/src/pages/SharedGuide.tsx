/**
 * 공유 링크 공개 가이드북 (비로그인)
 */
import { useEffect } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { ChangeLogItem, ScheduleCard } from "@/components/common/cards"
import { BasicHeader } from "@/components/layout/navigation"
import { toUiCongestion, useConfirmGuide } from "@/features/recommendation"

export default function SharedGuide() {
  const { token } = useParams()
  const navigate = useNavigate()
  const { guide, loading, error, loadPublic } = useConfirmGuide(undefined)

  useEffect(() => {
    if (token) void loadPublic(token)
  }, [token, loadPublic])

  return (
    <div className="relative flex flex-1 flex-col">
      <BasicHeader title="공유 가이드북" onBack={() => navigate(-1)} />
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
                    meta={stop.visitTime ?? ""}
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
          </>
        )}
      </div>
    </div>
  )
}
