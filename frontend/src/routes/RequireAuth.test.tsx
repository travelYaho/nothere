import { render, screen } from "@testing-library/react"
import { createMemoryRouter, RouterProvider } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import { RequireAuth } from "./RequireAuth"

let sessionState = {
  session: null as { access_token: string } | null,
  user: null,
  isLoading: false,
  isRecovery: false,
}

vi.mock("@/store/sessionStore", () => ({
  useSession: () => sessionState,
}))

function renderGuard(path = "/home") {
  const router = createMemoryRouter(
    [
      { path: "/login", element: <div>login-screen</div> },
      {
        element: <RequireAuth />,
        children: [{ path: "/home", element: <div>member-home</div> }],
      },
    ],
    { initialEntries: [path] },
  )
  return render(<RouterProvider router={router} />)
}

describe("RequireAuth", () => {
  it("세션을 확인하는 동안 회원 화면을 그리지 않는다", () => {
    sessionState = { session: null, user: null, isLoading: true, isRecovery: false }
    renderGuard()
    expect(screen.queryByText("member-home")).not.toBeInTheDocument()
    expect(screen.queryByText("login-screen")).not.toBeInTheDocument()
  })

  it("비회원은 로그인 화면으로 보낸다", () => {
    sessionState = { session: null, user: null, isLoading: false, isRecovery: false }
    renderGuard()
    expect(screen.getByText("login-screen")).toBeInTheDocument()
    expect(screen.queryByText("member-home")).not.toBeInTheDocument()
  })

  it("로그인한 사용자는 회원 화면을 보여준다", () => {
    sessionState = {
      session: { access_token: "token" },
      user: null,
      isLoading: false,
      isRecovery: false,
    }
    renderGuard()
    expect(screen.getByText("member-home")).toBeInTheDocument()
    expect(screen.queryByText("login-screen")).not.toBeInTheDocument()
  })
})
