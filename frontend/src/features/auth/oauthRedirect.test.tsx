import { render, screen } from "@testing-library/react"
import { createMemoryRouter, RouterProvider } from "react-router-dom"
import { describe, expect, it } from "vitest"
import { OauthCodeCatcher } from "./OauthCodeCatcher"
import {
  oauthCallbackPath,
  resolveOAuthRedirectUrl,
  shouldForwardOAuthCode,
} from "./oauthRedirect"

describe("resolveOAuthRedirectUrl", () => {
  const origin = "https://nothere-3b9c.vercel.app"

  it("비어 있거나 URL이 아니면 현재 origin의 콜백을 쓴다", () => {
    expect(resolveOAuthRedirectUrl("", origin)).toBe(`${origin}/auth/callback`)
    expect(resolveOAuthRedirectUrl("kakao-rest-key", origin)).toBe(`${origin}/auth/callback`)
  })

  it("사이트 루트 redirect는 콜백 경로로 고친다", () => {
    expect(resolveOAuthRedirectUrl(origin, origin)).toBe(`${origin}/auth/callback`)
    expect(resolveOAuthRedirectUrl(`${origin}/`, origin)).toBe(`${origin}/auth/callback`)
  })

  it("올바른 콜백 URL은 그대로 쓴다", () => {
    expect(resolveOAuthRedirectUrl("http://localhost:5173/auth/callback", origin)).toBe(
      "http://localhost:5173/auth/callback",
    )
  })
})

describe("shouldForwardOAuthCode", () => {
  it("루트나 로그인에 남은 code를 콜백으로 보낸다", () => {
    expect(shouldForwardOAuthCode("/", "?code=abc")).toBe(true)
    expect(shouldForwardOAuthCode("/login", "?code=abc")).toBe(true)
  })

  it("콜백 경로는 다시 보내지 않는다", () => {
    expect(shouldForwardOAuthCode("/auth/callback", "?code=abc")).toBe(false)
    expect(shouldForwardOAuthCode("/", "")).toBe(false)
  })

  it("콜백 경로 문자열을 만든다", () => {
    expect(oauthCallbackPath("?code=abc")).toBe("/auth/callback?code=abc")
  })
})

describe("OauthCodeCatcher", () => {
  it("게스트 홈의 ?code= 를 /auth/callback 으로 보낸다", () => {
    const router = createMemoryRouter(
      [
        {
          element: <OauthCodeCatcher />,
          children: [
            { path: "/", element: <div>guest-home</div> },
            { path: "/auth/callback", element: <div>oauth-callback</div> },
          ],
        },
      ],
      { initialEntries: ["/?code=oauth-code"] },
    )

    render(<RouterProvider router={router} />)
    expect(screen.getByText("oauth-callback")).toBeInTheDocument()
    expect(screen.queryByText("guest-home")).not.toBeInTheDocument()
  })
})
