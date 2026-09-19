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
  const { error } = await supabase.auth.signInWithOAuth({
    provider: "kakao",
    options: { redirectTo, skipBrowserRedirect: false },
  })
  if (error) throw error
}

export function ensureProfile() {
  return apiClient.post<UserResponse>("/auth/ensure-profile")
}

/** 카카오 OAuth 콜백 URL의 code를 세션으로 바꾸고 서비스 profile을 보정한다. */
export async function completeOAuthCallback(search: string) {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search)
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
