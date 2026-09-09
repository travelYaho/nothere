/**
 * Login — 로그인 / 회원가입 / 비밀번호 찾기 화면.
 * Figma: 여기말GO / node 48:3448 "로그인 화면"
 */
import { useMemo, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useAuth } from "@/auth/AuthProvider"
import { requestPasswordReset } from "@/lib/api"
import { ChevronLeft } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { FieldLabel, PasswordInput, TextInput } from "@/components/common/inputs"

type View = "login" | "signup" | "reset"

function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, signup } = useAuth()

  const initialView: View = searchParams.get("tab") === "signup" ? "signup" : "login"
  const [view, setView] = useState<View>(initialView)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [passwordConfirm, setPasswordConfirm] = useState("")
  const [nickname, setNickname] = useState("")
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [resetDone, setResetDone] = useState(false)

  const title = useMemo(() => {
    if (view === "reset") return "비밀번호 찾기"
    return "여기말고"
  }, [view])

  const goBack = () => {
    if (view === "reset") {
      setView("login")
      setFormError(null)
      setFieldErrors({})
      setResetDone(false)
      return
    }
    navigate(-1)
  }

  const validateAuth = () => {
    const next: Record<string, string> = {}
    if (!email.trim()) next.email = "이메일을 입력해 주세요."
    else if (!isValidEmail(email.trim())) next.email = "이메일 형식을 확인해주세요."
    if (!password) next.password = "비밀번호를 입력해 주세요."
    else if (password.length < 8) next.password = "비밀번호는 8자 이상이어야 합니다."
    if (view === "signup") {
      if (!nickname.trim()) next.nickname = "닉네임을 입력해 주세요."
      if (passwordConfirm !== password) next.passwordConfirm = "비밀번호가 일치하지 않습니다."
    }
    setFieldErrors(next)
    return Object.keys(next).length === 0
  }

  const onSubmitAuth = async () => {
    setFormError(null)
    if (!validateAuth()) return
    setBusy(true)
    try {
      if (view === "signup") {
        await signup(email.trim(), password, nickname.trim())
      } else {
        await login(email.trim(), password)
      }
      navigate("/home", { replace: true })
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "요청에 실패했습니다.")
    } finally {
      setBusy(false)
    }
  }

  const onSubmitReset = async () => {
    setFormError(null)
    const next: Record<string, string> = {}
    if (!email.trim()) next.email = "이메일을 입력해 주세요."
    else if (!isValidEmail(email.trim())) next.email = "이메일 형식을 확인해주세요."
    setFieldErrors(next)
    if (Object.keys(next).length > 0) return
    setBusy(true)
    try {
      await requestPasswordReset(email.trim())
      setResetDone(true)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "요청에 실패했습니다.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center px-5 py-2">
        <button
          type="button"
          onClick={goBack}
          className="-ml-1 rounded-full p-1 text-ink hover:bg-ink/5"
        >
          <ChevronLeft size={22} />
        </button>
      </div>

      <div className="flex flex-1 flex-col items-center px-6 pt-3">
        <div className="flex w-full max-w-[325px] flex-col items-center">
          <h1 className="text-[24px] font-extrabold tracking-[-0.72px] text-ink">{title}</h1>
          <p className="mt-1 text-center text-[13px] font-medium text-ink-muted">
            {view === "reset"
              ? "가입한 이메일로 재설정 안내를 보내드립니다."
              : "혼잡한 곳만 바꿔주는 일정 점검"}
          </p>
        </div>

        {view !== "reset" && (
          <div className="mt-6 flex w-full max-w-[325px] border-b-[0.667px] border-line-soft">
            <button
              type="button"
              onClick={() => {
                setView("login")
                setFormError(null)
                setFieldErrors({})
              }}
              className={[
                "flex-1 pb-3 text-center text-[15px] font-bold",
                view === "login" ? "text-ink" : "text-ink-ghost",
              ].join(" ")}
            >
              로그인
            </button>
            <button
              type="button"
              onClick={() => {
                setView("signup")
                setFormError(null)
                setFieldErrors({})
              }}
              className={[
                "flex-1 pb-3 text-center text-[15px] font-bold",
                view === "signup" ? "text-ink" : "text-ink-ghost",
              ].join(" ")}
            >
              회원가입
            </button>
          </div>
        )}

        {view === "reset" ? (
          <form
            className="mt-6 flex w-full max-w-[325px] flex-col"
            onSubmit={(e) => {
              e.preventDefault()
              void onSubmitReset()
            }}
          >
            <FieldLabel required>이메일</FieldLabel>
            <TextInput
              placeholder="이메일"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={fieldErrors.email}
            />
            {resetDone && (
              <p className="pt-3 text-[13px] font-medium text-ink-soft">
                비밀번호 재설정 안내를 보냈습니다.
              </p>
            )}
            {formError && (
              <p className="pt-3 text-[13px] font-medium text-congestion-high">{formError}</p>
            )}
            <div className="mt-4">
              <Button block loading={busy} type="submit">
                재설정 메일 보내기
              </Button>
            </div>
          </form>
        ) : (
          <form
            className="flex w-full max-w-[325px] flex-col items-stretch"
            onSubmit={(e) => {
              e.preventDefault()
              void onSubmitAuth()
            }}
          >
            <div className="mt-5 flex flex-col gap-3">
              {view === "signup" && (
                <div>
                  <FieldLabel required>닉네임</FieldLabel>
                  <TextInput
                    placeholder="닉네임"
                    autoComplete="nickname"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    error={fieldErrors.nickname}
                  />
                </div>
              )}
              <div>
                <FieldLabel required>이메일</FieldLabel>
                <TextInput
                  placeholder="이메일"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  error={fieldErrors.email}
                />
              </div>
              <div>
                <FieldLabel required>비밀번호</FieldLabel>
                <PasswordInput
                  placeholder="비밀번호"
                  autoComplete={view === "signup" ? "new-password" : "current-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  error={fieldErrors.password}
                />
              </div>
              {view === "signup" && (
                <div>
                  <FieldLabel required>비밀번호 확인</FieldLabel>
                  <PasswordInput
                    placeholder="비밀번호 확인"
                    autoComplete="new-password"
                    value={passwordConfirm}
                    onChange={(e) => setPasswordConfirm(e.target.value)}
                    error={fieldErrors.passwordConfirm}
                  />
                </div>
              )}
            </div>

            {formError && (
              <p className="mt-3 text-[13px] font-medium text-congestion-high">{formError}</p>
            )}

            <div className="mt-4">
              <Button block loading={busy} type="submit">
                {view === "signup" ? "가입하기" : "로그인"}
              </Button>
            </div>

            <div className="mt-3 flex items-center justify-between px-1">
              <button
                type="button"
                className="text-[12px] font-medium text-ink-muted"
                onClick={() => {
                  setView("reset")
                  setFormError(null)
                  setFieldErrors({})
                  setResetDone(false)
                }}
              >
                비밀번호 찾기
              </button>
              <button
                type="button"
                className="text-[12px] font-medium text-ink-muted"
                onClick={() => {
                  setView("signup")
                  setFormError(null)
                  setFieldErrors({})
                }}
              >
                이메일로 가입하기
              </button>
            </div>

            <div className="mt-4 flex items-center gap-3">
              <span className="h-px flex-1 bg-line-soft" />
              <span className="shrink-0 text-[11px] font-medium text-ink-ghost">간편 로그인</span>
              <span className="h-px flex-1 bg-line-soft" />
            </div>

            <div className="mt-4 flex flex-col gap-2.5 pb-8">
              <Button variant="ghost" block disabled type="button">
                소셜 A로 계속하기
              </Button>
              <Button variant="ghost" block disabled type="button">
                소셜 B로 계속하기
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
