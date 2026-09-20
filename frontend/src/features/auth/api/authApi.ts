/**
 * 인증 도메인 API 호출 함수.
 *
 * 로그인/로그아웃은 백엔드를 거치지 않고 Supabase Auth를 직접 호출한다
 * (backend/app/api/v1/auth.py 주석과 동일한 설계). 회원가입과 OAuth 첫 로그인의
 * profile 생성만 백엔드(/auth/signup, /auth/ensure-profile)를 거친다.
 */
import { apiClient } from "@/api/apiClient"
import { supabase } from "@/api/supabaseClient"
import type { SignupRequest, SignupResponse, UserResponse } from "@/features/auth/types"

function extractErrorText(err: unknown): string {
  if (err instanceof Error) return err.message
  if (typeof err === "string") return err
  if (err && typeof err === "object") {
    const body = err as { msg?: unknown; message?: unknown; error_description?: unknown }
    for (const value of [body.msg, body.message, body.error_description]) {
      if (typeof value === "string" && value.trim()) return value
    }
  }
  return ""
}

export function toKakaoLoginErrorMessage(err: unknown): string {
  const raw = extractErrorText(err)
  if (/failed to fetch|network/i.test(raw)) {
    return "서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."
  }
  if (/provider is not enabled|unsupported provider/i.test(raw)) {
    return "카카오 로그인이 아직 켜져 있지 않습니다. Supabase Authentication > Providers > Kakao를 활성화한 뒤 다시 시도해 주세요."
  }
  return raw.trim() || "카카오 로그인에 실패했습니다."
}

export async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw error
  return data
}

export async function signInWithKakao() {
  const redirectTo = import.meta.env.VITE_OAUTH_REDIRECT_URL
  if (!redirectTo) {
    throw new Error(
      "카카오 로그인 설정이 없습니다. frontend/.env 의 VITE_OAUTH_REDIRECT_URL 을 확인하세요.",
    )
  }

  // skipBrowserRedirect: authorize URL로 바로 이동하면 provider 미활성 시
  // 브라우저가 JSON 에러 페이지만 보여주고, 로그인 화면 로딩이 안 풀린다.
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "kakao",
    options: { redirectTo, skipBrowserRedirect: true },
  })
  if (error) throw new Error(toKakaoLoginErrorMessage(error))

  const url = data.url
  if (!url) throw new Error("카카오 로그인에 실패했습니다.")

  let probe: Response
  try {
    probe = await fetch(url, { redirect: "manual" })
  } catch {
    window.location.assign(url)
    return
  }

  if (probe.type === "opaqueredirect" || (probe.status >= 300 && probe.status < 400)) {
    window.location.assign(url)
    return
  }

  if (!probe.ok) {
    let payload: unknown = { msg: probe.statusText }
    try {
      payload = await probe.json()
    } catch {
      // JSON 이 아니면 statusText 로 폴백한다.
    }
    throw new Error(toKakaoLoginErrorMessage(payload))
  }

  window.location.assign(url)
}

export function ensureProfile() {
  return apiClient.post<UserResponse>("/auth/ensure-profile")
}

function shareInFlight<T>(cache: Map<string, Promise<T>>, key: string, run: () => Promise<T>): Promise<T> {
  const existing = cache.get(key)
  if (existing) return existing
  const promise = run().finally(() => {
    cache.delete(key)
  })
  cache.set(key, promise)
  return promise
}

function callbackSearchKey(search: string) {
  return search.startsWith("?") ? search : `?${search}`
}

function callbackParams(search: string) {
  return new URLSearchParams(callbackSearchKey(search).slice(1))
}

const oauthCallbackInFlight = new Map<string, Promise<UserResponse>>()

async function runOAuthCallback(search: string) {
  const params = callbackParams(search)
  const oauthError = params.get("error_description") || params.get("error")
  if (oauthError) {
    throw new Error(oauthError)
  }
  const code = params.get("code")
  if (!code) {
    throw new Error("카카오 로그인에 실패했습니다.")
  }
  const { error } = await supabase.auth.exchangeCodeForSession(code)
  if (error) throw error
  return ensureProfile()
}

/** 카카오 OAuth 콜백 URL의 code를 세션으로 바꾸고 서비스 profile을 보정한다. */
export function completeOAuthCallback(search: string) {
  const key = callbackSearchKey(search)
  return shareInFlight(oauthCallbackInFlight, key, () => runOAuthCallback(key))
}

const passwordRecoveryInFlight = new Map<string, Promise<void>>()

async function runPasswordRecovery(search: string) {
  const params = callbackParams(search)
  const recoveryError = params.get("error_description") || params.get("error")
  if (recoveryError) {
    throw new Error(recoveryError)
  }
  const code = params.get("code")
  if (!code) {
    throw new Error("만료되었거나 유효하지 않은 링크예요.")
  }
  const { error } = await supabase.auth.exchangeCodeForSession(code)
  if (error) throw error
}

/** 비밀번호 재설정 메일의 PKCE code를 복구 세션으로 바꾼다. */
export function completePasswordRecovery(search: string) {
  const key = callbackSearchKey(search)
  return shareInFlight(passwordRecoveryInFlight, key, () => runPasswordRecovery(key))
}

export async function signOut() {
  const { error } = await supabase.auth.signOut()
  if (error) throw error
}

/** 백엔드 signup 응답의 토큰을 프론트 Supabase 클라이언트 세션으로 반영한다. */
export async function establishSession(accessToken: string, refreshToken: string) {
  const { error } = await supabase.auth.setSession({
    access_token: accessToken,
    refresh_token: refreshToken,
  })
  if (error) throw error
}

export function signUp(payload: SignupRequest) {
  return apiClient.post<SignupResponse>("/auth/signup", payload)
}

/** 비밀번호 재설정 메일 발송 — 메일 링크는 /reset-password 로 돌아온다. */
export async function requestPasswordReset(email: string) {
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/reset-password`,
  })
  if (error) throw error
}

/** 재설정 링크로 만들어진 세션에서 새 비밀번호로 변경한다. */
export async function updatePassword(password: string) {
  const { error } = await supabase.auth.updateUser({ password })
  if (error) throw error
}
