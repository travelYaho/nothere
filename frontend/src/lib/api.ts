import { API_BASE_URL } from "./supabase"

export type HomeResponse = {
  user: { id: string; nickname: string }
  draftSchedule: {
    scheduleId: string
    title: string
    travelDate: string | null
    status: string
  } | null
  recentSchedules: {
    scheduleId: string
    title: string
    travelDate: string | null
    status: string
  }[]
}

export type UserResponse = {
  id: string
  email: string
  nickname: string
  profileImageUrl: string | null
}

export type AuthSessionResponse = {
  user: UserResponse
  accessToken?: string | null
  refreshToken?: string | null
  tokenType?: string | null
}

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>
    const err = record.error as Record<string, unknown> | undefined
    if (typeof err?.message === "string") return err.message
    if (typeof record.message === "string") return record.message
  }
  return fallback
}

async function parseJson(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined
  return response.json().catch(() => ({}))
}

async function apiFetch<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(init?.headers ?? {}),
    },
  })
  const body = await parseJson(response)
  if (!response.ok) {
    throw new Error(errorMessage(body, `요청 실패 (${response.status})`))
  }
  return body as T
}

async function publicPost<T>(path: string, payload: unknown, fallback: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  const body = await parseJson(response)
  if (!response.ok) {
    throw new Error(errorMessage(body, fallback))
  }
  return body as T
}

export function fetchHome(accessToken: string) {
  return apiFetch<HomeResponse>("/api/home", accessToken)
}

export function fetchMe(accessToken: string) {
  return apiFetch<UserResponse>("/api/users/me", accessToken)
}

export function signup(payload: { email: string; password: string; nickname: string }) {
  return publicPost<AuthSessionResponse>(
    "/api/auth/signup",
    payload,
    "회원가입에 실패했습니다.",
  )
}

export function login(payload: { email: string; password: string }) {
  return publicPost<AuthSessionResponse>("/api/auth/login", payload, "로그인에 실패했습니다.")
}

export function logout(accessToken: string) {
  return apiFetch<void>("/api/auth/logout", accessToken, { method: "POST" })
}

export function requestPasswordReset(email: string) {
  return publicPost<{ message: string }>(
    "/api/auth/password/reset-request",
    { email },
    "재설정 요청에 실패했습니다.",
  )
}
