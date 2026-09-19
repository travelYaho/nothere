/**
 * AuthCallback이 OAuth code 교환 후 홈으로 보내고, 실패 시 로그인으로 되돌리는지 확인한다.
 */
import { render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import AuthCallback from "./AuthCallback"

const mockNavigate = vi.fn()
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

vi.mock("@/features/auth", () => ({
  completeOAuthCallback: vi.fn(),
}))

import { completeOAuthCallback } from "@/features/auth"

const completeOAuthCallbackMock = vi.mocked(completeOAuthCallback)

describe("AuthCallback", () => {
  beforeEach(() => {
    mockNavigate.mockReset()
    completeOAuthCallbackMock.mockReset()
  })

  it("성공하면 홈으로 보낸다", async () => {
    completeOAuthCallbackMock.mockResolvedValue({
      id: "user-1",
      email: "kakao@example.com",
      nickname: "말고마니",
      profileImageUrl: null,
    })

    render(<AuthCallback />)

    expect(screen.getByText("카카오 로그인 처리 중...")).toBeInTheDocument()
    await waitFor(() => {
      expect(completeOAuthCallbackMock).toHaveBeenCalledWith(window.location.search)
      expect(mockNavigate).toHaveBeenCalledWith("/home", { replace: true })
    })
  })

  it("실패하면 로그인 화면으로 에러를 넘긴다", async () => {
    completeOAuthCallbackMock.mockRejectedValue(new Error("인가가 취소되었습니다."))

    render(<AuthCallback />)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/login", {
        replace: true,
        state: { error: "인가가 취소되었습니다." },
      })
    })
  })
})
