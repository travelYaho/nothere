/**
 * fetch 기반 최소 API 클라이언트.
 *
 * README 컨벤션: 최상위 src/api 는 "클라이언트 설정"만 담당한다 — 실제
 * 엔드포인트 호출 함수는 features/{domain}/api 에 둔다.
 *
 * 라이브러리(axios 등) 추가는 팀 합의 후 나중에 교체해도 되도록, 호출부는
 * apiClient.get/post/patch/put/delete 인터페이스만 알면 되게 분리했다.
 */
import { getAccessToken } from "@/store/sessionStore"
import { ApiError, NetworkError, type ApiErrorBody, type ApiSuccessBody } from "@/types/api"

// VITE_API_BASE_URL 은 "/api" 없는 원본 도메인이다(lib/api.ts 와 공유하는 컨벤션).
const BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api`

type QueryParams = Record<string, string | number | boolean | undefined | null>

interface RequestOptions {
  params?: QueryParams
  body?: unknown
  signal?: AbortSignal
}

function buildUrl(path: string, params?: QueryParams): string {
  const base = BASE_URL.replace(/\/+$/, "")
  const cleanPath = path.replace(/^\/+/, "")
  const url = new URL(`${base}/${cleanPath}`)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value))
    }
  }
  return url.toString()
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const url = buildUrl(path, options.params)
  const token = await getAccessToken()

  const headers: Record<string, string> = { Accept: "application/json" }
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body !== undefined) headers["Content-Type"] = "application/json"

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    })
  } catch (cause) {
    throw new NetworkError(cause)
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
