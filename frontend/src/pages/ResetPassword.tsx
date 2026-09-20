/**
 * ResetPassword — 메일의 재설정 링크로 들어와 새 비밀번호를 설정한다.
 *
 * detectSessionInUrl 이 꺼져 있으므로, URL 의 PKCE code 는 이 화면에서
 * exchangeCodeForSession 으로 직접 교환한다. 교환 실패·복구 세션 없음일 때만
 * 만료 링크로 본다.
 */
import { useEffect, useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/common/primitives"
import { PasswordInput } from "@/components/common/inputs"
import { completePasswordRecovery, signOut, updatePassword } from "@/features/auth"
import { markPasswordRecovery, useSession } from "@/store/sessionStore"

function toErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    if (/failed to fetch|network/i.test(err.message)) {
      return "서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."
    }
    if (/different from the old password/i.test(err.message)) {
      return "이전과 다른 비밀번호를 입력해 주세요."
    }
    return err.message
  }
  return "요청 중 문제가 발생했습니다."
}

function hasRecoveryCode(search: string) {
  return Boolean(new URLSearchParams(search.startsWith("?") ? search.slice(1) : search).get("code"))
}

export default function ResetPassword() {
  const navigate = useNavigate()
  const { session, isLoading, isRecovery } = useSession()
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [exchanging, setExchanging] = useState(() => hasRecoveryCode(window.location.search))
  const [exchangeFailed, setExchangeFailed] = useState(false)
  const [exchangedOk, setExchangedOk] = useState(false)

  useEffect(() => {
    const search = window.location.search
    if (!hasRecoveryCode(search)) {
      setExchanging(false)
      return
    }

    let cancelled = false
    setExchanging(true)
    setExchangeFailed(false)
    completePasswordRecovery(search)
      .then(() => {
        if (cancelled) return
        markPasswordRecovery()
        setExchangedOk(true)
        window.history.replaceState({}, "", "/reset-password")
      })
      .catch(() => {
        if (!cancelled) setExchangeFailed(true)
      })
      .finally(() => {
        if (!cancelled) setExchanging(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError("비밀번호가 일치하지 않아요.")
      return
    }
    setLoading(true)
    try {
      await updatePassword(password)
      // 재설정용 임시 세션은 정리하고 새 비밀번호로 다시 로그인하게 한다.
      await signOut().catch(() => undefined)
      setDone(true)
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const waiting = exchanging || isLoading
  const recoveryReady = exchangedOk || (isRecovery && Boolean(session))
  const expired = !waiting && (exchangeFailed || !recoveryReady)

  return (
    <div className="flex flex-1 flex-col items-center px-6 pt-14">
      <div className="flex w-full max-w-[325px] flex-col">
        <h1 className="text-[22px] font-extrabold tracking-[-0.66px] text-ink">새 비밀번호 설정</h1>

        {done ? (
          <div className="mt-6 flex flex-col gap-4">
            <p className="text-[13px] leading-[19px] font-medium text-ink-soft">
              비밀번호가 변경됐어요. 새 비밀번호로 로그인해 주세요.
            </p>
            <Button block onClick={() => navigate("/login", { replace: true })}>
              로그인하러 가기
            </Button>
          </div>
        ) : waiting ? (
          <p className="mt-6 text-[13px] text-ink-muted">확인하는 중...</p>
        ) : expired ? (
          <div className="mt-6 flex flex-col gap-4">
            <p className="text-[13px] leading-[19px] font-medium text-congestion-high">
              만료되었거나 유효하지 않은 링크예요. 재설정 메일을 다시 요청해 주세요.
            </p>
            <Button block onClick={() => navigate("/forgot-password", { replace: true })}>
              재설정 메일 다시 받기
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-2.5">
            <PasswordInput
              placeholder="새 비밀번호 (6자 이상)"
              required
              minLength={6}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <PasswordInput
              placeholder="새 비밀번호 확인"
              required
              minLength={6}
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
            {error && <p className="text-[12px] font-medium text-congestion-high">{error}</p>}
            <div className="mt-1">
              <Button type="submit" block loading={loading}>
                비밀번호 변경
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
