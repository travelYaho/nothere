/**
 * 카카오 OAuth 에러 메시지와 PKCE code 교환 중복 호출을 검증한다.
 */
import { describe, expect, it, vi, beforeEach } from "vitest"

const { exchangeCodeForSession, apiPost } = vi.hoisted(() => ({
  exchangeCodeForSession: vi.fn(),
  apiPost: vi.fn(),
}))

vi.mock("@/api/supabaseClient", () => ({
  supabase: {
    auth: {
      signInWithOAuth: vi.fn(),
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
      setSession: vi.fn(),
      exchangeCodeForSession,
    },
  },
}))
vi.mock("@/api/apiClient", () => ({
  apiClient: { post: apiPost },
}))

import { completeOAuthCallback, completePasswordRecovery, toKakaoLoginErrorMessage } from "./authApi"

describe("toKakaoLoginErrorMessage", () => {
  it("provider 미활성 JSON을 안내 문구로 바꾼다", () => {
    expect(
      toKakaoLoginErrorMessage({
        code: 400,
        error_code: "validation_failed",
        msg: "Unsupported provider: provider is not enabled",
      }),
    ).toMatch(/카카오 로그인이 아직 켜져 있지 않습니다/)
  })

  it("일반 Error 메시지는 그대로 둔다", () => {
    expect(toKakaoLoginErrorMessage(new Error("인가가 취소되었습니다."))).toBe(
      "인가가 취소되었습니다.",
    )
  })
})

describe("PKCE code 교환", () => {
  beforeEach(() => {
    exchangeCodeForSession.mockReset()
    apiPost.mockReset()
    apiPost.mockResolvedValue({
      id: "user-1",
      email: "kakao@example.com",
      nickname: "말고마니",
      profileImageUrl: null,
    })
  })

  it("같은 OAuth callback은 code 교환을 한 번만 한다", async () => {
    let resolveExchange: (value: { error: null }) => void = () => undefined
    exchangeCodeForSession.mockReturnValue(
      new Promise((resolve) => {
        resolveExchange = resolve
      }),
    )

    const first = completeOAuthCallback("?code=abc")
    const second = completeOAuthCallback("?code=abc")
    resolveExchange({ error: null })

    await Promise.all([first, second])
    expect(exchangeCodeForSession).toHaveBeenCalledTimes(1)
    expect(exchangeCodeForSession).toHaveBeenCalledWith("abc")
    expect(apiPost).toHaveBeenCalledTimes(1)
  })

  it("같은 재설정 링크는 code 교환을 한 번만 한다", async () => {
    let resolveExchange: (value: { error: null }) => void = () => undefined
    exchangeCodeForSession.mockReturnValue(
      new Promise((resolve) => {
        resolveExchange = resolve
      }),
    )

    const first = completePasswordRecovery("?code=recov")
    const second = completePasswordRecovery("?code=recov")
    resolveExchange({ error: null })

    await Promise.all([first, second])
    expect(exchangeCodeForSession).toHaveBeenCalledTimes(1)
    expect(exchangeCodeForSession).toHaveBeenCalledWith("recov")
  })
})
