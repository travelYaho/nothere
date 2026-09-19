/**
 * AuthCallback — 카카오 OAuth PKCE 콜백.
 * Supabase가 code를 세션으로 바꾼 뒤 서비스 profile을 보정하고 홈으로 보낸다.
 */
import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Spinner } from "@/components/common/primitives"
import { completeOAuthCallback } from "@/features/auth"

function toErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    if (/failed to fetch|network/i.test(err.message)) {
      return "서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."
    }
    return err.message
  }
  return "카카오 로그인에 실패했습니다."
}

export default function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false
    completeOAuthCallback(window.location.search)
      .then(() => {
        if (!cancelled) navigate("/home", { replace: true })
      })
      .catch((err) => {
        if (!cancelled) {
          navigate("/login", { replace: true, state: { error: toErrorMessage(err) } })
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
