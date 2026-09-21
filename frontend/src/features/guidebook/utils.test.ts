import { describe, expect, it } from "vitest"
import { coverMetaLine, displayGuideTitle, guideKicker, shortPlaceLabel } from "./utils"
import type { GuideResponse } from "@/features/recommendation/types/part3"

describe("guidebook utils", () => {
  it("guideKicker strips 구 and uppercases latin", () => {
    expect(guideKicker("종로구", "서울")).toBe("종로 GUIDE")
    expect(guideKicker("", "서울")).toBe("서울 GUIDE")
  })

  it("coverMetaLine joins date, region, travel", () => {
    const guide = {
      tripId: "1",
      title: "서촌 당일치기",
      travelDate: "2026-08-15",
      cityName: "서울",
      districtName: "종로구",
      totalTravelMin: 66,
      status: "confirmed",
      stops: [],
      entries: [],
    } satisfies GuideResponse
    expect(coverMetaLine(guide)).toBe("2026.08.15 · 서울 종로구 · 이동 66분")
    expect(shortPlaceLabel(guide)).toEqual({ city: "서울", district: "종로구" })
  })

  it("displayGuideTitle strips auto-generated date prefix", () => {
    expect(displayGuideTitle("2026.09.25 커플 여행")).toBe("커플 여행")
    expect(displayGuideTitle("서촌 당일치기")).toBe("서촌 당일치기")
    expect(displayGuideTitle("2026.09.25")).toBe("2026.09.25")
  })
})
