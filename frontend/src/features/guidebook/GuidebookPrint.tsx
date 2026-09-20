import { GuideCoverPage } from "./GuideCoverPage"
import { GuideInnerPage } from "./GuideInnerPage"
import type { GuideResponse } from "@/features/recommendation/types/part3"

/** 인쇄/PDF용 정적 펼침 — page-flip 트랜스폼은 인쇄에 안 나온다. */
export function GuidebookPrint({
  guide,
  memoReadOnly,
}: {
  guide: GuideResponse
  memoReadOnly?: boolean
}) {
  return (
    <div className="guidebook-print hidden print:block">
      <section className="break-after-page">
        <GuideCoverPage guide={guide} />
      </section>
      <section>
        <GuideInnerPage guide={guide} memoReadOnly={memoReadOnly ?? true} />
      </section>
    </div>
  )
}
