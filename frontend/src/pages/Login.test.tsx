/**
 * Login 카카오 버튼과 OAuth 콜백 에러 표시를 확인한다.
 */
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import Login from "./Login"

vi.mock("@/features/auth", () => ({
  signIn: vi.fn(),
  signUp: vi.fn(),
  establishSession: vi.fn(),
  signInWithKakao: vi.fn(),
  toKakaoLoginErrorMessage: (err: unknown) => {
    const raw = err instanceof Error ? err.message : String(err ?? "")
    if (/provider is not enabled|unsupported provider/i.test(raw)) {
      return "카카오 로그인이 아직 켜져 있지 않습니다. Supabase Authentication > Providers > Kakao를 활성화한 뒤 다시 시도해 주세요."
    }
    return raw || "카카오 로그인에 실패했습니다."
  },
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

    expect(screen.getByRole("img", { name: "카카오 로그인" })).toHaveAttribute(
      "src",
      "/images/kakao_login_large_wide.png",
    )
    await user.click(screen.getByRole("button", { name: "카카오 로그인" }))

    expect(signInWithKakaoMock).toHaveBeenCalledTimes(1)
  })

  it("콜백에서 넘어온 에러를 팝업으로 보여준다", () => {
    renderLogin({ error: "카카오 로그인에 실패했습니다." })
    expect(screen.getByRole("alertdialog")).toBeInTheDocument()
    expect(screen.getByText("카카오 로그인에 실패했어요")).toBeInTheDocument()
    expect(screen.getByText("카카오 로그인에 실패했습니다.")).toBeInTheDocument()
  })

  it("provider 미활성 에러를 안내 팝업으로 보여준다", async () => {
    const user = userEvent.setup()
    signInWithKakaoMock.mockRejectedValue(
      new Error("Unsupported provider: provider is not enabled"),
    )
    renderLogin()

    await user.click(screen.getByRole("button", { name: "카카오 로그인" }))

    expect(await screen.findByRole("alertdialog")).toBeInTheDocument()
    expect(screen.getByText(/카카오 로그인이 아직 켜져 있지 않습니다/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "카카오 로그인" })).not.toBeDisabled()
  })

  it("카카오 시작이 실패하면 팝업을 띄운다", async () => {
    const user = userEvent.setup()
    signInWithKakaoMock.mockRejectedValue(new Error("카카오 로그인 설정이 없습니다."))
    renderLogin()

    await user.click(screen.getByRole("button", { name: "카카오 로그인" }))

    expect(await screen.findByRole("alertdialog")).toBeInTheDocument()
    expect(screen.getByText("카카오 로그인에 실패했어요")).toBeInTheDocument()
    expect(screen.getByText("카카오 로그인 설정이 없습니다.")).toBeInTheDocument()
  })

  it("팝업에서 닫기를 누르면 사라진다", async () => {
    const user = userEvent.setup()
    renderLogin({ error: "카카오 로그인에 실패했습니다." })

    const dialog = screen.getByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "닫기" }))

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
  })
})
