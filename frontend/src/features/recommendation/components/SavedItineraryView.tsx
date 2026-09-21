import savedHero from "@/assets/images/saved-hero.jpg"
import { ChevronLeft } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { formatVisitTime } from "@/features/trips/utils/placeOrder"
import { formatDottedDate } from "@/utils/date"
import type { GuideResponse, GuideStop } from "../types/part3"

function congestionPhrase(level: string | null | undefined): string | null {
  if (level === "high") return "혼잡 예상"
  if (level === "mid" || level === "medium") return "보통 예상"
  if (level === "low") return "여유 예상"
  return null
}

function changeLogDetail(stop: GuideStop): string | null {
  const parts: string[] = []
  const extra = stop.extraMinutes
  if (extra != null) {
    if (extra > 0) parts.push(`이동 ${extra}분 증가`)
    else if (extra < 0) parts.push(`이동 ${Math.abs(extra)}분 감소`)
    else parts.push("이동 시간 동일")
  }
  const fromPhrase = congestionPhrase(stop.beforeLevel)
  const toPhrase = congestionPhrase(stop.afterLevel)
  if (fromPhrase && toPhrase) parts.push(`${fromPhrase} → ${toPhrase}`)
  return parts.length > 0 ? parts.join(". ") : null
}

export function SavedItineraryView({
  guide,
  onBack,
  onEdit,
  onMakeGuidebook,
  onHome,
}: {
  guide: GuideResponse
  onBack?: () => void
  onEdit: () => void
  onMakeGuidebook?: () => void
  onHome: () => void
}) {
  const coverSrc = guide.coverImageUrl || savedHero
  const metaLine = [
    guide.travelDate ? formatDottedDate(guide.travelDate) : null,
    guide.regionName,
  ]
    .filter(Boolean)
    .join(" · ")
  const changeLogs = guide.stops.filter((stop) => stop.wasReplaced && stop.replacedFrom)

  return (
    <div className="relative flex min-h-dvh flex-1 flex-col overflow-hidden bg-canvas">
      <div className="flex flex-1 flex-col overflow-y-auto">
        <div className="relative h-[168px] w-full shrink-0 overflow-hidden bg-primary">
          <img
            src={coverSrc}
            alt=""
            className="absolute inset-0 size-full object-cover opacity-35"
          />
          <div
            className="absolute inset-0"
            style={{
              backgroundImage:
                "linear-gradient(0deg, rgb(58, 143, 96) 0%, rgba(58, 143, 96, 0.85) 25%, rgba(58, 143, 96, 0.7) 50%, rgba(58, 143, 96, 0.55) 75%, rgba(58, 143, 96, 0.475) 87.5%, rgba(58, 143, 96, 0.4) 100%)",
            }}
          />
          {onBack && (
            <button
              type="button"
              onClick={onBack}
              className="absolute left-3 top-3 z-10 rounded-full p-1 text-white print:hidden"
              aria-label="뒤로"
            >
              <ChevronLeft size={22} />
            </button>
          )}
          <div className="relative flex h-full flex-col items-center justify-center px-4 text-center">
            <p className="text-[10px] font-bold leading-[15px] tracking-[1.6px] text-white/70">
              TRIPCHECK GUIDEBOOK
            </p>
            <p className="pt-1.5 text-[22px] font-extrabold leading-[33px] tracking-[-0.44px] text-white">
              {guide.title}
            </p>
            {metaLine && (
              <p className="pt-1 text-[12px] font-medium leading-[18px] text-white/80">{metaLine}</p>
            )}
          </div>
        </div>

        <div className="flex flex-col px-4 pt-5">
          <p className="px-1 text-[15px] font-extrabold leading-[22.5px] tracking-[-0.3px] text-ink">
            일정
          </p>

          {guide.stops.length === 0 ? (
            <p className="py-10 text-center text-[13px] text-ink-muted">등록된 장소가 없어요.</p>
          ) : (
            <div className="flex flex-col gap-2 pt-2">
              {guide.stops.map((stop) => (
                <div
                  key={`${stop.position}-${stop.placeName}`}
                  className="flex items-center gap-3 rounded-2xl bg-surface px-4 py-3.5 shadow-[0px_1px_1px_rgba(0,0,0,0.05)]"
                >
                  <p className="shrink-0 text-[12px] font-bold leading-[18px] text-primary">
                    {formatVisitTime(stop.visitTime) || "--:--"}
                  </p>
                  <p className="min-w-0 flex-1 truncate text-[14px] font-bold leading-[21px] text-ink">
                    {stop.placeName}
                  </p>
                  {stop.stayMinutes != null && (
                    <p className="shrink-0 text-[11px] font-medium leading-[16.5px] text-ink-faint">
                      {stop.stayMinutes}분
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          <p className="px-1 pt-5 text-[15px] font-extrabold leading-[22.5px] tracking-[-0.3px] text-ink">
            변경 기록
          </p>
          <div className="flex flex-col gap-2 pt-2">
            {changeLogs.length === 0 ? (
              <div className="rounded-2xl bg-surface px-4 py-3.5 shadow-[0px_1px_1px_rgba(0,0,0,0.05)]">
                <p className="text-[13px] font-medium leading-[21px] text-ink-muted">
                  변경된 장소가 없어요.
                </p>
              </div>
            ) : (
              changeLogs.map((stop) => {
                const detail = changeLogDetail(stop)
                return (
                  <div
                    key={`change-${stop.position}-${stop.placeName}`}
                    className="rounded-2xl bg-surface px-4 py-3.5 shadow-[0px_1px_1px_rgba(0,0,0,0.05)]"
                  >
                    <p className="text-[13px] font-bold leading-[21.125px] text-ink">
                      {stop.replacedFrom} → {stop.placeName}
                    </p>
                    {detail && (
                      <p className="text-[13px] font-normal leading-[21.125px] text-[#6b8675]">
                        {detail}
                      </p>
                    )}
                  </div>
                )
              })
            )}
          </div>

          <div className="h-3" />
        </div>
      </div>

      <div className="border-t-[0.667px] border-line-soft bg-white/95 px-4 pb-6 pt-3">
        <div className="flex gap-2.5">
          <Button variant="primary" onClick={onEdit} className="h-[54px] min-w-0 flex-1">
            수정하기
          </Button>
          {onMakeGuidebook && (
            <button
              type="button"
              onClick={onMakeGuidebook}
              className="inline-flex h-[54px] min-w-0 flex-1 items-center justify-center rounded-[var(--radius-field)] bg-primary px-3 text-center text-[15px] font-extrabold leading-[19px] tracking-[-0.16px] text-primary-foreground shadow-[var(--shadow-primary)] transition-[transform,filter,opacity] hover:brightness-[1.05] active:scale-[0.99]"
            >
              가이드북
              <br />
              만들기
            </button>
          )}
          <Button
            variant="ghost"
            onClick={onHome}
            className="h-[54px] w-[100px] shrink-0 px-4 text-[15px] font-bold"
          >
            홈으로
          </Button>
        </div>
      </div>
    </div>
  )
}
