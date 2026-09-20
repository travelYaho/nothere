/**
 * 잘못된 redirectTo 로 루트에 떨어진 PKCE code 를 /auth/callback 으로 넘긴다.
 */
import { Navigate, Outlet, useLocation } from "react-router-dom"
import { oauthCallbackPath, shouldForwardOAuthCode } from "@/features/auth/oauthRedirect"

export function OauthCodeCatcher() {
  const location = useLocation()
  if (shouldForwardOAuthCode(location.pathname, location.search)) {
    return <Navigate to={oauthCallbackPath(location.search, location.hash)} replace />
  }
  return <Outlet />
}
