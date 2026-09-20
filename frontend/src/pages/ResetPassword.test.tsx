/**
 * 재설정 메일 링크의 PKCE code를 교환한 뒤에만 만료 여부를 판단하는지 확인한다.
 */
import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

const completePasswordRecovery = vi.fn()
const markPasswordRecovery = vi.fn()
let sessionState = { session: null as { access_token: string } | null, user: null, isLoading: false, isRecovery: false }

vi.mock("@/features/auth", () => ({
  completePasswordRecovery: (...args: unknown[]) => completePasswordRecovery(...args),
  signOut: vi.fn(),
  updatePassword: vi.fn(),
}))

vi.mock("@/store/sessionStore", () => ({
  useSession: () => sessionState,
  markPasswordRecovery: (...args: unknown[]) => markPasswordRecovery(...args),
}))

import ResetPassword from "./ResetPassword"

describe("ResetPassword", () => {
  beforeEach(() => {
    completePasswordRecovery.mockReset()
    markPasswordRecovery.mockReset()
    sessionState = { session: null, user: null, isLoading: false, isRecovery: false }
    window.history.replaceState({}, "", "/reset-password")
  })

  it("code가 없고 복구 세션도 없으면 만료로 본다", () => {
    render(
      <MemoryRouter>
        <ResetPassword />
      </MemoryRouter>,
    )
    expect(screen.getByText(/만료되었거나 유효하지 않은 링크예요/)).toBeInTheDocument()
    expect(completePasswordRecovery).not.toHaveBeenCalled()
  })

  it("code가 있으면 교환이 끝난 뒤에 폼을 보여준다", async () => {
    window.history.replaceState({}, "", "/reset-password?code=abc")
    completePasswordRecovery.mockResolvedValue(undefined)

    render(
      <MemoryRouter>
        <ResetPassword />
      </MemoryRouter>,
    )

    expect(screen.getByText("확인하는 중...")).toBeInTheDocument()
    await waitFor(() => {
      expect(completePasswordRecovery).toHaveBeenCalledWith("?code=abc")
      expect(markPasswordRecovery).toHaveBeenCalled()
      expect(screen.getByRole("button", { name: "비밀번호 변경" })).toBeInTheDocument()
    })
    expect(window.location.pathname).toBe("/reset-password")
    expect(window.location.search).toBe("")
  })

  it("code 교환이 실패하면 만료로 본다", async () => {
    window.history.replaceState({}, "", "/reset-password?code=bad")
    completePasswordRecovery.mockRejectedValue(new Error("invalid"))

    render(
      <MemoryRouter>
        <ResetPassword />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText(/만료되었거나 유효하지 않은 링크예요/)).toBeInTheDocument()
    })
    expect(markPasswordRecovery).not.toHaveBeenCalled()
  })
})
