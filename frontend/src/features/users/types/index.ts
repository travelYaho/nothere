/** backend/app/schemas/user.py 와 짝을 이루는 타입들. */
export type { UserResponse } from "@/features/auth/types"

export interface UserStatsResponse {
  totalTripCount: number
  confirmedTripCount: number
}
