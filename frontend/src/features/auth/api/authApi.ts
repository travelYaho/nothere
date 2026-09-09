/**
 * 인증 도메인 API 호출 함수.
 *
 * 로그인/로그아웃은 백엔드를 거치지 않고 Supabase Auth를 직접 호출한다
 * (backend/app/api/v1/auth.py 주석과 동일한 설계). 회원가입만 profile 레코드
 * 생성이 필요해서 백엔드 POST /auth/signup 을 거친다.
 */
import { apiClient } from "@/api/apiClient"
import { supabase } from "@/api/supabaseClient"
import type { SignupRequest, SignupResponse } from "@/features/auth/types"

export async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw error
  return data
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
