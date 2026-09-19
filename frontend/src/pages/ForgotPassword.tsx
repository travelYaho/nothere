/**
 * ForgotPassword — 비밀번호 찾기: 이메일로 재설정 링크를 보낸다.
 */
import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { ChevronLeft } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { TextInput } from "@/components/common/inputs"
import { requestPasswordReset } from "@/features/auth"

function toErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    if (/failed to fetch|network/i.test(err.message)) {
      return "서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."
    }
    if (/rate limit|too many/i.test(err.message)) {
      return "요청이 너무 많아요. 잠시 후 다시 시도해 주세요."
    }
    return err.message
  }
  return "요청 중 문제가 발생했습니다."
}

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await requestPasswordReset(email.trim())
      setSent(true)
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center px-5 py-2">
        <button
          onClick={() => navigate(-1)}
          aria-label="뒤로가기"
          className="-ml-1 rounded-full p-1 text-ink hover:bg-ink/5"
        >
          <ChevronLeft size={22} />
        </button>
      </div>

      <div className="flex flex-1 flex-col items-center px-6 pt-3">
        <div className="flex w-full max-w-[325px] flex-col">
          <h1 className="text-[22px] font-extrabold tracking-[-0.66px] text-ink">비밀번호 찾기</h1>
          <p className="mt-1.5 text-[13px] leading-[19px] font-medium text-ink-muted">
            가입한 이메일을 입력하면 비밀번호 재설정 링크를 보내드려요.
          </p>
        </div>

        {sent ? (
          <div className="mt-6 flex w-full max-w-[325px] flex-col gap-4">
            <p className="text-[13px] leading-[19px] font-medium text-ink-soft">
              {email} 으로 재설정 메일을 보냈어요. 메일의 링크를 눌러 새 비밀번호를 설정해 주세요.
              메일이 보이지 않으면 스팸함도 확인해 주세요.
            </p>
            <Button block onClick={() => navigate("/login", { replace: true })}>
              로그인으로 돌아가기
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-6 flex w-full max-w-[325px] flex-col gap-2.5">
            <TextInput
              placeholder="이메일"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {error && <p className="text-[12px] font-medium text-congestion-high">{error}</p>}
            <div className="mt-1">
              <Button type="submit" block loading={loading}>
                재설정 메일 보내기
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
