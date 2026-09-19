/**
 * 카카오 OAuth 에러 메시지를 사용자 안내로 바꿉니다.
 */
import { describe, expect, it, vi } from "vitest"

vi.mock("@/api/supabaseClient", () => ({
  supabase: { auth: { signInWithOAuth: vi.fn(), signInWithPassword: vi.fn(), signOut: vi.fn(), setSession: vi.fn(), exchangeCodeForSession: vi.fn() } },
}))
vi.mock("@/api/apiClient", () => ({
  apiClient: { post: vi.fn() },
}))

import { toKakaoLoginErrorMessage } from "./authApi"

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
