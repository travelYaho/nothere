import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"
import { GuidebookBook } from "./GuidebookBook"
import type { GuideResponse } from "@/features/recommendation/types/part3"

const guide: GuideResponse = {
  tripId: "trip-1",
  title: "서촌 당일치기",
  travelDate: "2026-08-15",
  cityName: "서울",
  districtName: "종로구",
  status: "confirmed",
  stops: [
    {
      position: 1,
      placeName: "통인시장",
      visitTime: "12:00",
      wasReplaced: false,
      replacedFrom: null,
      replaceReason: null,
      travelToNext: null,
      imageUrl: null,
    },
  ],
  entries: [],
  memo: "",
}

describe("GuidebookBook", () => {
  it("오른쪽 화살표로 속지를 연다", async () => {
    const user = userEvent.setup()
    render(
      <GuidebookBook
        guide={guide}
        onShare={() => undefined}
        onHome={() => undefined}
      />,
    )

    expect(screen.getByLabelText("일정으로")).toBeInTheDocument()
    expect(screen.getByTestId("guidebook-cover-sheet")).toHaveStyle({
      transform: "rotateY(0deg)",
    })
    await user.click(screen.getByLabelText("일정으로"))
    expect(screen.getByTestId("guidebook-cover-sheet")).toHaveStyle({
      transform: "rotateY(-180deg)",
    })
    expect(screen.getByLabelText("표지로")).toBeInTheDocument()
    expect(screen.queryByLabelText("일정으로")).not.toBeInTheDocument()
  })

  it("표지를 누르면 속지로 이동한다", async () => {
    const user = userEvent.setup()
    render(<GuidebookBook guide={guide} onShare={() => undefined} onHome={() => undefined} />)
    await user.click(screen.getByRole("button", { name: /서울/ }))
    expect(screen.getByLabelText("표지로")).toBeInTheDocument()
  })
})
