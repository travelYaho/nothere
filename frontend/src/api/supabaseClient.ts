/**
 * Supabase 클라이언트 인스턴스.
 *
 * 로그인/로그아웃/토큰 갱신은 백엔드를 거치지 않고 프론트가 Supabase Auth를
 * 직접 사용한다(백엔드 app/api/v1/auth.py 주석과 동일한 설계). 세션은
 * supabase-js가 기본적으로 localStorage에 저장/자동 갱신한다.
 */
import { createClient } from "@supabase/supabase-js"

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

if (!supabaseUrl || !supabaseKey) {
  throw new Error(
    "VITE_SUPABASE_URL / VITE_SUPABASE_PUBLISHABLE_KEY 가 설정되지 않았습니다. frontend/.env 를 확인하세요.",
  )
}

export const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: {
    // PKCE code 교환은 /auth/callback 에서 명시적으로 한다.
    // 기본값(true)이면 클라이언트 초기화와 페이지 effect가 같은 code를 두 번 쓸 수 있다.
    detectSessionInUrl: false,
    flowType: "pkce",
  },
})
