import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import SharedGuide from "./SharedGuide"

vi.mock("@/features/recommendation", () => ({
  useConfirmGuide: () => ({
    guide: {
      tripId: "trip-1",
      title: "서촌 당일치기",
      travelDate: "2026-08-15",
      cityName: "서울",
      districtName: "종로구",
      status: "confirmed",
      stops: [],
      entries: [],
      memo: "",
    },
    loading: false,
    error: null,
    loadPublic: vi.fn(),
  }),
}))

describe("SharedGuide home", () => {
  it("홈 로고는 로그인 홈으로 보낸다", async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={["/guide/abc"]}>
        <Routes>
          <Route path="/guide/:token" element={<SharedGuide />} />
          <Route path="/" element={<div>guest-home</div>} />
          <Route path="/home" element={<div>logged-in-home</div>} />
        </Routes>
      </MemoryRouter>,
    )
    await user.click(screen.getByRole("button", { name: "홈" }))
    expect(screen.getByText("logged-in-home")).toBeInTheDocument()
    expect(screen.queryByText("guest-home")).not.toBeInTheDocument()
  })
})
