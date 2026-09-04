import type { CompanionType } from "@/features/trips/types"

/** STEP2/STEP3 화면에서 공통으로 쓰는 동행유형 표시 라벨. */
export const COMPANION_LABELS: Record<CompanionType, string> = {
  solo: "혼자",
  couple: "연인",
  friends: "친구",
  family: "가족",
}
