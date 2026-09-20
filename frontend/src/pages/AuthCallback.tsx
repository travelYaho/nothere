/**
 * AuthCallback — 카카오 OAuth PKCE 콜백.
 * Supabase가 code를 세션으로 바꾼 뒤 서비스 profile을 보정하고 홈으로 보낸다.
 */
import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Spinner } from "@/components/common/primitives"
import { completeOAuthCallback, toKakaoLoginErrorMessage } from "@/features/auth"

const oauthCallbackInFlight = new Map<string, ReturnType<typeof completeOAuthCallback>>()

export default function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    const search = window.location.search
    let pending = oauthCallbackInFlight.get(search)
    if (!pending) {
      pending = completeOAuthCallback(search).finally(() => {
        oauthCallbackInFlight.delete(search)
      })
      oauthCallbackInFlight.set(search, pending)
    }
    pending
      .then(() => {
        if (!cancelled) navigate("/home", { replace: true })
      })
      .catch((err) => {
        if (!cancelled) {
          navigate("/login", { replace: true, state: { error: toKakaoLoginErrorMessage(err) } })
        }
      })
    return () => {
      cancelled = true
    }
  }, [navigate])

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6">
      <Spinner />
      <p className="text-[13px] font-medium text-ink-muted">카카오 로그인 처리 중...</p>
    </div>
  )
}
