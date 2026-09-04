/** backend/app/schemas/auth.py, user.py 와 짝을 이루는 타입들. */
export interface SignupRequest {
  email: string
  password: string
  nickname: string
}

export interface UserResponse {
  id: string
  email: string
  nickname: string
  profileImageUrl: string | null
}

export interface SignupResponse {
  user: UserResponse
  accessToken?: string
  refreshToken?: string
  tokenType?: string
}
