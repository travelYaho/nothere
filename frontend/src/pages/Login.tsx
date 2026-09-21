/**
 * Login — 로그인 화면.
 * Figma: 여기말GO / node 48:3448 "로그인 화면"
 *
 * 소셜 로그인만 지원한다 — 이메일 로그인/회원가입 폼은 두지 않는다.
 * 첫 소셜 로그인이 곧 가입이다(profile 은 OAuth 콜백에서 ensure-profile 로 만든다).
 */
import { useEffect, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { ChevronLeft } from "@/components/common/icons"
import { AlertDialog } from "@/components/feedback/modals"
import { signInWithKakao, toKakaoLoginErrorMessage } from "@/features/auth"

function oauthErrorFromState(state: unknown): string | null {
  if (!state || typeof state !== "object" || !("error" in state)) return null
  const value = (state as { error?: unknown }).error
  return typeof value === "string" && value.trim() ? value : null
}

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const [kakaoError, setKakaoError] = useState<string | null>(() => oauthErrorFromState(location.state))
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

  async function handleKakaoLogin() {
    setKakaoError(null)
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

        <div className="mt-8 flex w-full max-w-[325px] items-center gap-3">
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
