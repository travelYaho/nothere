/** 카카오 OAuth 가 앱으로 돌아올 콜백 경로. */
export const OAUTH_CALLBACK_PATH = "/auth/callback"

export function resolveOAuthRedirectUrl(
  envValue: string | undefined = import.meta.env.VITE_OAUTH_REDIRECT_URL,
  origin: string = window.location.origin,
): string {
  const fallback = `${origin}${OAUTH_CALLBACK_PATH}`
  const raw = (envValue ?? "").trim()
  if (!raw) return fallback
  try {
    const url = new URL(raw)
    if (url.protocol !== "http:" && url.protocol !== "https:") return fallback
    const path = url.pathname.replace(/\/+$/, "") || "/"
    if (path !== OAUTH_CALLBACK_PATH) return fallback
    return `${url.origin}${OAUTH_CALLBACK_PATH}`
  } catch {
    return fallback
  }
}

export function shouldForwardOAuthCode(pathname: string, search: string): boolean {
  if (pathname === OAUTH_CALLBACK_PATH) return false
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search)
  return Boolean(params.get("code"))
}

export function oauthCallbackPath(search: string, hash = ""): string {
  const query = !search || search.startsWith("?") ? search : `?${search}`
  return `${OAUTH_CALLBACK_PATH}${query}${hash}`
}
