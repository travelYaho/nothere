/**
 * 로그인 세션 전역 상태. 2개 이상 도메인(auth, apiClient, 추후 STEP2~3 화면들)이
 * 공유하므로 README 컨벤션대로 src/store 에 둔다.
 *
 * - useSession(): 컴포넌트에서 세션을 구독할 때 쓴다.
 * - getAccessToken(): apiClient 처럼 React 밖에서 현재 토큰을 읽을 때 쓴다.
 */
import { useSyncExternalStore } from "react"
import type { Session, User } from "@supabase/supabase-js"
import { supabase } from "@/api/supabaseClient"

interface SessionState {
  session: Session | null
  user: User | null
  isLoading: boolean
  /** 비밀번호 재설정 메일 링크로 진입해 만들어진 복구 세션인지(일반 로그인 세션과 구분). */
  isRecovery: boolean
}

let state: SessionState = { session: null, user: null, isLoading: true, isRecovery: false }
const listeners = new Set<() => void>()

function setState(next: Partial<SessionState>) {
  state = { ...state, ...next }
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function getSnapshot() {
  return state
}

supabase.auth.getSession().then(({ data }) => {
  setState({ session: data.session, user: data.session?.user ?? null, isLoading: false })
})

supabase.auth.onAuthStateChange((event, session) => {
  // PASSWORD_RECOVERY 는 재설정 링크로 들어온 직후에만 발생한다. 로그아웃되면 해제한다.
  const isRecovery =
    event === "PASSWORD_RECOVERY" ? true : event === "SIGNED_OUT" ? false : state.isRecovery
  setState({ session, user: session?.user ?? null, isLoading: false, isRecovery })
})

export function useSession(): SessionState {
  return useSyncExternalStore(subscribe, getSnapshot)
}

/** 재설정 메일 링크의 code를 교환한 뒤, PASSWORD_RECOVERY 이벤트가 오기 전에 폼을 연다. */
export function markPasswordRecovery() {
  setState({ isRecovery: true, isLoading: false })
}

export async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

let refreshing: Promise<string | null> | null = null

/**
 * 서버가 토큰을 거부(401)했을 때 세션을 한 번 갱신해 새 토큰을 받는다. 실패하면 null.
 * 동시에 여러 요청이 401을 받아도 갱신은 한 번만 하도록 진행 중인 요청을 공유한다.
 */
export function refreshAccessToken(): Promise<string | null> {
  refreshing ??= supabase.auth
    .refreshSession()
    .then(({ data, error }) => (error ? null : (data.session?.access_token ?? null)))
    .catch(() => null)
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

/**
 * 갱신해도 서버가 토큰을 거부하면 로컬 세션을 지운다. 세션이 null이 되면
 * RequireAuth 가 /login 으로 보낸다. 토큰이 이미 무효라 서버 로그아웃 호출은 하지 않는다.
 */
export async function clearInvalidSession(): Promise<void> {
  await supabase.auth.signOut({ scope: "local" }).catch(() => undefined)
}
