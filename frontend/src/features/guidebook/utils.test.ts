import { describe, expect, it } from "vitest"
import { circledIndex, coverMetaLine, guideKicker, shortPlaceLabel } from "./utils"
import type { GuideResponse } from "@/features/recommendation/types/part3"

describe("guidebook utils", () => {
  it("circledIndex uses unicode badges up to 20", () => {
    expect(circledIndex(1)).toBe("①")
    expect(circledIndex(4)).toBe("④")
    expect(circledIndex(21)).toBe("21")
  })

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
})
