import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import HomeGuest from "./HomeGuest"

let sessionState = {
  session: null as { access_token: string } | null,
  user: null,
  isLoading: false,
  isRecovery: false,
}

vi.mock("@/store/sessionStore", () => ({
  useSession: () => sessionState,
}))

function renderGuest() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<HomeGuest />} />
        <Route path="/home" element={<div>logged-in-home</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe("HomeGuest", () => {
  it("비로그인은 게스트 홈을 보여준다", () => {
    sessionState = { session: null, user: null, isLoading: false, isRecovery: false }
    renderGuest()
    expect(screen.getByRole("button", { name: "로그인 / 회원가입" })).toBeInTheDocument()
  })

  it("로그인한 사용자는 로그인 홈으로 보낸다", () => {
    sessionState = {
      session: { access_token: "token" },
      user: null,
      isLoading: false,
      isRecovery: false,
    }
    renderGuest()
    expect(screen.getByText("logged-in-home")).toBeInTheDocument()
  })
})
