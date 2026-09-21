/** backend/app/schemas/user.py 와 짝을 이루는 타입. */
export interface UserResponse {
  id: string
  email: string
  nickname: string
  profileImageUrl: string | null
}
