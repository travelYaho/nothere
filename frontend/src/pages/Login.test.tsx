/**
 * Login 카카오 버튼과 OAuth 콜백 에러 표시를 확인한다.
 */
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import Login from "./Login"

vi.mock("@/features/auth", () => ({
  signIn: vi.fn(),
  signUp: vi.fn(),
  establishSession: vi.fn(),
  signInWithKakao: vi.fn(),
}))

import { signInWithKakao } from "@/features/auth"

const signInWithKakaoMock = vi.mocked(signInWithKakao)

function renderLogin(state?: { error?: string }) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/login", state }]}>
      <Login />
    </MemoryRouter>,
  )
}

describe("Login kakao", () => {
  beforeEach(() => {
    signInWithKakaoMock.mockReset()
    signInWithKakaoMock.mockResolvedValue(undefined)
  })

  it("카카오 버튼이 OAuth를 시작한다", async () => {
    const user = userEvent.setup()
    renderLogin()

    await user.click(screen.getByRole("button", { name: "카카오로 계속하기" }))

    expect(signInWithKakaoMock).toHaveBeenCalledTimes(1)
  })

  it("콜백에서 넘어온 에러를 보여준다", () => {
    renderLogin({ error: "카카오 로그인에 실패했습니다." })
    expect(screen.getByText("카카오 로그인에 실패했습니다.")).toBeInTheDocument()
  })
})
