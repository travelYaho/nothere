const ACCESS_KEY = "access_token"
const REFRESH_KEY = "refresh_token"

export function getAccessToken(): string {
  if (typeof window === "undefined") return ""
  return localStorage.getItem(ACCESS_KEY) || localStorage.getItem("sb-access-token") || ""
}

export function getRefreshToken(): string {
  if (typeof window === "undefined") return ""
  return localStorage.getItem(REFRESH_KEY) || ""
}

export function setSessionTokens(accessToken: string | null, refreshToken: string | null): void {
  if (typeof window === "undefined") return
  if (accessToken) {
    localStorage.setItem(ACCESS_KEY, accessToken)
  } else {
    localStorage.removeItem(ACCESS_KEY)
  }
  if (refreshToken) {
    localStorage.setItem(REFRESH_KEY, refreshToken)
  } else {
    localStorage.removeItem(REFRESH_KEY)
  }
}

export function clearSessionTokens(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem("sb-access-token")
}
