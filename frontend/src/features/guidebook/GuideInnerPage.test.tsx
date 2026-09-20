import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { GuideInnerPage } from "./GuideInnerPage"
import type { GuideResponse } from "@/features/recommendation/types/part3"

function guide(overrides: Partial<GuideResponse> = {}): GuideResponse {
  return {
    tripId: "trip-1",
    title: "서촌 당일치기",
    travelDate: "2026-08-15",
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
    ...overrides,
  }
}

describe("GuideInnerPage", () => {
  it("MEMO는 일정 리스트 아래에 렌더된다", () => {
    render(<GuideInnerPage guide={guide()} />)
    const place = screen.getByText("통인시장")
    const memo = screen.getByText("MEMO")
    expect(place.compareDocumentPosition(memo) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it("소유자 메모 입력 후 blur 시 저장한다", async () => {
    const user = userEvent.setup()
    const onSaveMemo = vi.fn().mockResolvedValue({ memo: "점심은 광장시장" })
    render(<GuideInnerPage guide={guide()} onSaveMemo={onSaveMemo} />)
    const box = screen.getByPlaceholderText("여행 메모를 입력하세요...")
    await user.type(box, "점심은 광장시장")
    box.blur()
    expect(onSaveMemo).toHaveBeenCalled()
  })

  it("제목에서 자동생성 날짜를 뺀다", () => {
    render(<GuideInnerPage guide={guide({ title: "2026.09.25 커플 여행" })} />)
    expect(screen.getByText("커플 여행")).toBeInTheDocument()
    expect(screen.queryByText("2026.09.25 커플 여행")).not.toBeInTheDocument()
  })
})
