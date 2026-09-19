/**
 * Login — 로그인 화면.
 * Figma: 여기말GO / node 48:3448 "로그인 화면"
 */
import { useEffect, useState, type FormEvent } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { ChevronLeft } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { PasswordInput, TextInput } from "@/components/common/inputs"
import { AlertDialog } from "@/components/feedback/modals"
import { establishSession, signIn, signInWithKakao, signUp, toKakaoLoginErrorMessage } from "@/features/auth"

function toErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    // supabase-js는 네트워크 실패 시 브라우저 fetch 의 원문 메시지("Failed to fetch")를
    // 그대로 던진다 — 사용자에게는 우리 말로 바꿔서 보여준다.
    if (/failed to fetch|network/i.test(err.message)) {
      return "서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."
    }
    return err.message
  }
  return "요청 중 문제가 발생했습니다."
}

function oauthErrorFromState(state: unknown): string | null {
  if (!state || typeof state !== "object" || !("error" in state)) return null
  const value = (state as { error?: unknown }).error
  return typeof value === "string" && value.trim() ? value : null
}

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [tab, setTab] = useState<"login" | "signup">("login")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [nickname, setNickname] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [kakaoError, setKakaoError] = useState<string | null>(() => oauthErrorFromState(location.state))
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [kakaoLoading, setKakaoLoading] = useState(false)

  useEffect(() => {
    function onPageShow(event: Event) {
      setKakaoLoading(false)
      const persisted = "persisted" in event && Boolean((event as PageTransitionEvent).persisted)
      if (persisted) {
        setKakaoError((current) => current ?? "카카오 로그인에 실패했습니다.")
      }
    }
    window.addEventListener("pageshow", onPageShow)
    return () => window.removeEventListener("pageshow", onPageShow)
  }, [])

  useEffect(() => {
    if (!oauthErrorFromState(location.state)) return
    navigate(location.pathname, { replace: true, state: {} })
  }, [location.pathname, location.state, navigate])

  function switchTab(next: "login" | "signup") {
    setTab(next)
    setError(null)
    setKakaoError(null)
    setNotice(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setNotice(null)
    setLoading(true)
    try {
      if (tab === "login") {
        await signIn(email, password)
        navigate("/home")
        return
      }

      const result = await signUp({ email, password, nickname })
      if (result.accessToken && result.refreshToken) {
        await establishSession(result.accessToken, result.refreshToken)
        navigate("/home")
      } else {
        setNotice("가입 확인 이메일을 보냈어요. 이메일을 확인한 뒤 로그인해 주세요.")
        switchTab("login")
      }
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleKakaoLogin() {
    setError(null)
    setKakaoError(null)
    setNotice(null)
    setKakaoLoading(true)
    try {
      await signInWithKakao()
    } catch (err) {
      setKakaoError(toKakaoLoginErrorMessage(err))
    } finally {
      setKakaoLoading(false)
    }
  }

  return (
    <div className="relative flex flex-1 flex-col">
      <div className="flex items-center px-5 py-2">
        <button
          onClick={() => navigate(-1)}
          className="-ml-1 rounded-full p-1 text-ink hover:bg-ink/5"
        >
          <ChevronLeft size={22} />
        </button>
      </div>

      <div className="flex flex-1 flex-col items-center px-6 pt-3">
        <div className="flex w-full max-w-[325px] flex-col items-center">
          <h1 className="text-[24px] font-extrabold tracking-[-0.72px] text-ink">여기말고</h1>
          <p className="mt-1 text-[13px] font-medium text-ink-muted">혼잡한 곳만 바꿔주는 일정 점검</p>
        </div>

        <div className="mt-6 flex w-full max-w-[325px] border-b-[0.667px] border-line-soft">
          <button
            onClick={() => switchTab("login")}
            className={[
              "flex-1 pb-3 text-center text-[15px] font-bold",
              tab === "login" ? "text-ink" : "text-ink-ghost",
            ].join(" ")}
          >
            로그인
          </button>
          <button
            onClick={() => switchTab("signup")}
            className={[
              "flex-1 pb-3 text-center text-[15px] font-bold",
              tab === "signup" ? "text-ink" : "text-ink-ghost",
            ].join(" ")}
          >
            회원가입
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 flex w-full max-w-[325px] flex-col gap-2.5">
          <TextInput
            placeholder="이메일"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <PasswordInput
            placeholder="비밀번호"
            required
            minLength={tab === "signup" ? 6 : undefined}
            autoComplete={tab === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {tab === "signup" && (
            <TextInput
              placeholder="닉네임"
              required
              maxLength={50}
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
            />
          )}

          {error && <p className="text-[12px] font-medium text-congestion-high">{error}</p>}
          {notice && <p className="text-[12px] font-medium text-ink-soft">{notice}</p>}

          <div className="mt-1">
            <Button type="submit" block loading={loading}>
              {tab === "login" ? "로그인" : "회원가입"}
            </Button>
          </div>
        </form>

        <div className="mt-3 flex w-full max-w-[325px] items-center justify-between px-1">
          <button className="text-[12px] font-medium text-ink-muted">비밀번호 찾기</button>
          <button className="text-[12px] font-medium text-ink-muted">이메일로 가입하기</button>
        </div>

        <div className="mt-4 flex w-full max-w-[325px] items-center gap-3">
          <span className="h-px flex-1 bg-line-soft" />
          <span className="shrink-0 text-[11px] font-medium text-ink-ghost">간편 로그인</span>
          <span className="h-px flex-1 bg-line-soft" />
        </div>

        <div className="mt-4 flex w-full max-w-[325px] flex-col gap-2.5 pb-8">
          <button
            type="button"
            onClick={handleKakaoLogin}
            disabled={kakaoLoading}
            aria-busy={kakaoLoading}
            className="block w-full disabled:pointer-events-none disabled:opacity-50"
          >
            <img
              src="/images/kakao_login_large_wide.png"
              alt="카카오 로그인"
              className="block h-auto w-full"
            />
          </button>
          <Button variant="ghost" block>
            소셜 B로 계속하기
          </Button>
        </div>
      </div>

      <AlertDialog
        open={kakaoError != null}
        title="카카오 로그인에 실패했어요"
        description={kakaoError ?? undefined}
        confirmLabel="다시 시도"
        cancelLabel="닫기"
        onConfirm={() => {
          void handleKakaoLogin()
        }}
        onCancel={() => setKakaoError(null)}
      />
    </div>
  )
}
