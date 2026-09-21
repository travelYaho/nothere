import { beforeEach, describe, expect, it, vi } from "vitest"

const session = vi.hoisted(() => ({
  getAccessToken: vi.fn(),
  refreshAccessToken: vi.fn(),
  clearInvalidSession: vi.fn(),
}))
vi.mock("@/store/sessionStore", () => session)

import { apiClient } from "@/api/apiClient"
import { ApiError } from "@/types/api"

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

const unauthorized = () =>
  jsonResponse(401, { error: { code: "AUTH_TOKEN_INVALID", message: "인증 토큰이 유효하지 않습니다." } })

const fetchMock = vi.fn()

beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal("fetch", fetchMock)
})

function authHeader(call: number) {
  return (fetchMock.mock.calls[call][1] as RequestInit).headers as Record<string, string>
}

describe("apiClient 401 처리", () => {
  it("401이면 세션을 갱신해 새 토큰으로 한 번 재시도한다", async () => {
    session.getAccessToken.mockResolvedValue("old")
    session.refreshAccessToken.mockResolvedValue("new")
    fetchMock.mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(jsonResponse(200, { data: { ok: true } }))

    await expect(apiClient.get("/me")).resolves.toEqual({ ok: true })

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(authHeader(0).Authorization).toBe("Bearer old")
    expect(authHeader(1).Authorization).toBe("Bearer new")
    expect(session.clearInvalidSession).not.toHaveBeenCalled()
  })

  it("재시도해도 401이면 로컬 세션을 지우고 에러를 던진다", async () => {
    session.getAccessToken.mockResolvedValue("old")
    session.refreshAccessToken.mockResolvedValue("new")
    fetchMock.mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(unauthorized())

    await expect(apiClient.get("/me")).rejects.toBeInstanceOf(ApiError)
    expect(session.clearInvalidSession).toHaveBeenCalledTimes(1)
  })

  it("세션 갱신에 실패하면 재시도 없이 로컬 세션을 지운다", async () => {
    session.getAccessToken.mockResolvedValue("old")
    session.refreshAccessToken.mockResolvedValue(null)
    fetchMock.mockResolvedValueOnce(unauthorized())

    await expect(apiClient.get("/me")).rejects.toMatchObject({ status: 401 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(session.clearInvalidSession).toHaveBeenCalledTimes(1)
  })

  it("토큰 없이 받은 401은 갱신·로그아웃을 시도하지 않는다", async () => {
    session.getAccessToken.mockResolvedValue(null)
    fetchMock.mockResolvedValueOnce(unauthorized())

    await expect(apiClient.get("/me")).rejects.toMatchObject({ status: 401 })
    expect(session.refreshAccessToken).not.toHaveBeenCalled()
    expect(session.clearInvalidSession).not.toHaveBeenCalled()
  })
})
