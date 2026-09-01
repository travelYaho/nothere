/**
 * Login — 로그인 화면.
 * Figma: 여기말GO / node 48:3448 "로그인 화면"
 */
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { ChevronLeft } from "@/components/common/icons"
import { Button } from "@/components/common/primitives"
import { PasswordInput, TextInput } from "@/components/common/inputs"

export default function Login() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<"login" | "signup">("login")

  return (
    <div className="flex flex-1 flex-col">
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
            onClick={() => setTab("login")}
            className={[
              "flex-1 pb-3 text-center text-[15px] font-bold",
              tab === "login" ? "text-ink" : "text-ink-ghost",
            ].join(" ")}
          >
            로그인
          </button>
          <button
            onClick={() => setTab("signup")}
            className={[
              "flex-1 pb-3 text-center text-[15px] font-bold",
              tab === "signup" ? "text-ink" : "text-ink-ghost",
            ].join(" ")}
          >
            회원가입
          </button>
        </div>

        <div className="mt-5 flex w-full max-w-[325px] flex-col gap-2.5">
          <TextInput placeholder="이메일" type="email" />
          <PasswordInput placeholder="비밀번호" />
        </div>

        <div className="mt-4 w-full max-w-[325px]">
          <Button block onClick={() => navigate("/home")}>
            로그인
          </Button>
        </div>

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
          <Button variant="ghost" block>
            소셜 A로 계속하기
          </Button>
          <Button variant="ghost" block>
            소셜 B로 계속하기
          </Button>
        </div>
      </div>
    </div>
  )
}
