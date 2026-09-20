import { coverMetaLine, displayGuideTitle, guideKicker, shortPlaceLabel } from "./utils"
import type { GuideResponse } from "@/features/recommendation/types/part3"

export function GuideCoverPage({
  guide,
  onOpenInner,
}: {
  guide: GuideResponse
  onOpenInner?: () => void
}) {
  const { city, district } = shortPlaceLabel(guide)
  const kicker = guideKicker(district, city)

  return (
    <div
      role={onOpenInner ? "button" : undefined}
      tabIndex={onOpenInner ? 0 : undefined}
      onClick={onOpenInner}
      onKeyDown={
        onOpenInner
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault()
                onOpenInner()
              }
            }
          : undefined
      }
      className="flex h-full w-full flex-col items-stretch overflow-hidden bg-[#fafbfd] text-left"
    >
      <div className="relative h-[58%] min-h-[280px] w-full shrink-0 overflow-hidden bg-[#16182a]">
        {guide.coverImageUrl ? (
          <img
            src={guide.coverImageUrl}
            alt=""
            className="absolute inset-0 size-full object-cover"
          />
        ) : null}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-black/10 to-[#16182a]/80" />
        <div className="absolute left-6 top-[52px] rounded-[6px] bg-white/15 px-3 py-1.5">
          <p className="text-[10px] font-extrabold tracking-[2px] text-white/80">
            TRIPCHECK GUIDEBOOK
          </p>
        </div>
        <div className="absolute bottom-[38px] left-5 right-5 font-black leading-[0.95] tracking-[-2px] text-white">
          {city ? <p className="text-[clamp(44px,18vw,72px)]">{city}</p> : null}
          {district ? <p className="text-[clamp(44px,18vw,72px)]">{district}</p> : null}
          {!city && !district ? <p className="text-[40px]">{displayGuideTitle(guide.title)}</p> : null}
        </div>
      </div>
      <div className="h-1 w-full shrink-0 bg-[#16182a]" />
      <div className="flex min-h-0 flex-1 flex-col bg-[#fafbfd]">
        <div className="flex items-center justify-between bg-[#16182a] px-6 py-3.5 text-[11px] font-semibold tracking-[0.5px] text-white/70">
          <p className="w-full text-center">{coverMetaLine(guide)}</p>
        </div>
        <div className="flex flex-col gap-3 px-6 pb-4 pt-7">
          <p className="text-[11px] font-extrabold tracking-[1.5px] text-[#1864f5]">{kicker}</p>
          <p className="text-[32px] font-extrabold leading-10 tracking-[-0.6px] text-ink">
            {displayGuideTitle(guide.title)}
          </p>
          {guide.tags && guide.tags.length > 0 ? (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[13px] font-bold text-[#667385]">
              {guide.tags.map((tag, i) => (
                <span key={tag} className="inline-flex items-center gap-3">
                  {i > 0 ? <span className="font-normal text-[#99a6b2]">·</span> : null}
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
