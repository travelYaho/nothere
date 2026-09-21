/**
 * fetch 기반 최소 API 클라이언트.
 *
 * README 컨벤션: 최상위 src/api 는 "클라이언트 설정"만 담당한다 — 실제
 * 엔드포인트 호출 함수는 features/{domain}/api 에 둔다.
 *
 * 라이브러리(axios 등) 추가는 팀 합의 후 나중에 교체해도 되도록, 호출부는
 * apiClient.get/post/patch/put/delete 인터페이스만 알면 되게 분리했다.
 */
import { API_BASE_URL } from "@/lib/apiBaseUrl"
import { clearInvalidSession, getAccessToken, refreshAccessToken } from "@/store/sessionStore"
import { ApiError, NetworkError, type ApiErrorBody, type ApiSuccessBody } from "@/types/api"

const BASE_URL = API_BASE_URL ? `${API_BASE_URL}/api` : "/api"

type QueryParams = Record<string, string | number | boolean | undefined | null>

interface RequestOptions {
  params?: QueryParams
  body?: unknown
  signal?: AbortSignal
}

function buildUrl(path: string, params?: QueryParams): string {
  const base = BASE_URL.replace(/\/+$/, "")
  const cleanPath = path.replace(/^\/+/, "")
  const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin
  const url = new URL(`${base}/${cleanPath}`, origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value))
    }
  }
  return url.toString()
}

async function send(
  method: string,
  url: string,
  token: string | null,
  options: RequestOptions,
): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" }
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body !== undefined) headers["Content-Type"] = "application/json"

  try {
    return await fetch(url, {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    })
  } catch (cause) {
    throw new NetworkError(cause)
  }
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const url = buildUrl(path, options.params)
  const token = await getAccessToken()

  let response = await send(method, url, token, options)

  // 토큰을 보냈는데 401이면 세션을 한 번 갱신해 재시도하고, 그래도 안 되면 로컬 세션을 지워
  // RequireAuth 가 로그인 화면으로 보내게 한다. 토큰 없이 받은 401은 세션이 원래 없는 것이라 그대로 둔다.
  if (response.status === 401 && token) {
    const refreshed = await refreshAccessToken()
    if (refreshed) response = await send(method, url, refreshed, options)
    if (response.status === 401) await clearInvalidSession()
  }

  if (response.status === 204) {
    return undefined as T
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch (cause) {
    if (!response.ok) {
      throw new ApiError(response.status, {
        code: "UNKNOWN_ERROR",
        message: response.statusText || "요청이 실패했습니다.",
      })
    }
    throw new NetworkError(cause)
  }

  if (!response.ok) {
    const body = (payload as { error?: ApiErrorBody }).error
    throw new ApiError(
      response.status,
      body ?? { code: "UNKNOWN_ERROR", message: "요청이 실패했습니다." },
    )
  }

  return (payload as ApiSuccessBody<T>).data
}

export const apiClient = {
  get: <T>(path: string, params?: QueryParams, signal?: AbortSignal) =>
    request<T>("GET", path, { params, signal }),
  post: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>("POST", path, { body, signal }),
  patch: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>("PATCH", path, { body, signal }),
  put: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>("PUT", path, { body, signal }),
  delete: <T = void>(path: string, signal?: AbortSignal) =>
    request<T>("DELETE", path, { signal }),
}
