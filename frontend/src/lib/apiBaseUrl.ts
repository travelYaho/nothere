/**
 * 백엔드 origin. `/api` 접두사는 붙이지 않는다.
 *
 * `npm run dev` 에서는 빈 문자열을 써서 fetch 가 같은 origin 의 `/api` 로 가게 한다.
 * Vite 가 그 요청을 로컬 백엔드로 프록시하므로, LAN IP 로 프론트를 열어도
 * 브라우저가 `localhost:8000` 을 치지 않는다.
 *
 * 배포 빌드만 `VITE_API_BASE_URL` 을 쓴다.
 */
export function resolveApiBaseUrl(
  env: { DEV: boolean; VITE_API_BASE_URL?: string } = import.meta.env,
): string {
  if (env.DEV) return ""
  return String(env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "") || "http://localhost:8000"
}

export const API_BASE_URL = resolveApiBaseUrl()
