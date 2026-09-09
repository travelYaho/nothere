import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"
import {
  fetchMe,
  login as loginRequest,
  logout as logoutRequest,
  signup as signupRequest,
  type UserResponse,
} from "@/lib/api"
import { clearSessionTokens, getAccessToken, setSessionTokens } from "@/lib/session"

type AuthContextValue = {
  user: UserResponse | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, nickname: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function applySession(user: UserResponse, accessToken?: string | null, refreshToken?: string | null) {
  if (accessToken) {
    setSessionTokens(accessToken, refreshToken ?? null)
  }
  return user
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null)

  useEffect(() => {
    const token = getAccessToken()
    if (!token) return
    fetchMe(token)
      .then(setUser)
      .catch(() => {
        clearSessionTokens()
        setUser(null)
      })
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const session = await loginRequest({ email, password })
    if (!session.accessToken) {
      throw new Error("이메일 확인 후 다시 로그인해 주세요.")
    }
    setUser(applySession(session.user, session.accessToken, session.refreshToken))
  }, [])

  const signup = useCallback(async (email: string, password: string, nickname: string) => {
    const session = await signupRequest({ email, password, nickname })
    if (!session.accessToken) {
      throw new Error("가입은 완료되었습니다. 이메일 확인 후 로그인해 주세요.")
    }
    setUser(applySession(session.user, session.accessToken, session.refreshToken))
  }, [])

  const logout = useCallback(async () => {
    const token = getAccessToken()
    try {
      if (token) await logoutRequest(token)
    } finally {
      clearSessionTokens()
      setUser(null)
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user && getAccessToken()),
      login,
      signup,
      logout,
    }),
    [user, login, signup, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error("useAuth 는 AuthProvider 안에서만 사용할 수 있습니다.")
  }
  return ctx
}
