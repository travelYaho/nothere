import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { GuideScheduleItem } from "./GuideScheduleItem"
import type { GuideStop } from "@/features/recommendation/types/part3"

function stop(overrides: Partial<GuideStop> = {}): GuideStop {
  return {
    position: 1,
    placeName: "통인시장",
    visitTime: "12:00",
    wasReplaced: false,
    replacedFrom: null,
    replaceReason: null,
    travelToNext: null,
    imageUrl: null,
    ...overrides,
  }
}

describe("GuideScheduleItem", () => {
  it("사진이 없으면 썸네일을 렌더하지 않는다", () => {
    const { container } = render(
      <GuideScheduleItem stop={stop({ imageUrl: null })} index={1} showConnector={false} />,
    )
    expect(container.querySelector("img")).toBeNull()
    expect(screen.getByText("통인시장")).toBeInTheDocument()
  })

  it("사진이 있으면 썸네일을 렌더한다", () => {
    const { container } = render(
      <GuideScheduleItem
        stop={stop({ imageUrl: "https://img.example/place.jpg" })}
        index={2}
        showConnector={false}
      />,
    )
    expect(container.querySelector("img")).toHaveAttribute(
      "src",
      "https://img.example/place.jpg",
    )
  })
})
