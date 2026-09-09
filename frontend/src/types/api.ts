/**
 * 백엔드 공통 응답 포맷과 짝을 이루는 타입들이다.
 * (backend/app/schemas/common.py 의 ApiResponse[T] / ApiError 참고)
 *
 * 성공: { data: T, meta?: ... }
 * 실패: { error: { code, message, ...extra } }
 */
export interface ApiSuccessBody<T> {
  data: T
  meta?: Record<string, unknown> | null
}

export interface ApiErrorBody {
  code: string
  message: string
  [extra: string]: unknown
}

/** 실패 응답(4xx/5xx)을 그대로 담아 던지는 에러. 화면에서 err.code 로 분기한다. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly extra: Record<string, unknown>

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = "ApiError"
    this.status = status
    this.code = body.code
    const { code: _code, message: _message, ...extra } = body
    this.extra = extra
  }
}

/** fetch 자체가 실패(네트워크 끊김, CORS 등)했을 때 던지는 에러. */
export class NetworkError extends Error {
  readonly cause: unknown

  constructor(cause: unknown) {
    super("서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요.")
    this.name = "NetworkError"
    this.cause = cause
  }
}
