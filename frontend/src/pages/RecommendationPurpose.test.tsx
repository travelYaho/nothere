/**
 * RecommendationPurpose(STEP5) — 태그 선택 후 AlternativeSearchLoading으로 이동만
 * 확인한다. 실제 검색(create/scoreRoutes)과 후보 0건 처리는 이제 그 화면으로 옮겨져서
 * 이 컴포넌트는 더 이상 그 로직을 갖지 않는다(2026-09-19, develop 병합 — 팀 다른
 * 브랜치가 STEP5→"searching" 로딩 화면 경유 흐름으로 리팩터함).
 */
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import RecommendationPurpose from "./RecommendationPurpose"

vi.mock("@/store/sessionStore", () => ({
  useSession: () => ({ session: { access_token: "test-token" }, user: null, isLoading: false }),
}))

const mockNavigate = vi.fn()
let mockLocationState: unknown = null
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ tripId: "trip-1", tripPlaceId: "tp-1" }),
    useLocation: () => ({
      state: mockLocationState,
      pathname: "",
      search: "",
      hash: "",
      key: "test",
    }),
  }
})

vi.mock("@/features/recommendation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/recommendation")>()
  return {
    ...actual,
    useExperienceTags: vi.fn(),
    fetchAnalysis: vi.fn(),
  }
})

import { fetchAnalysis, useExperienceTags } from "@/features/recommendation"

const useExperienceTagsMock = vi.mocked(useExperienceTags)
const fetchAnalysisMock = vi.mocked(fetchAnalysis)

beforeEach(() => {
  mockNavigate.mockReset()
  mockLocationState = null
  useExperienceTagsMock.mockReset()
  fetchAnalysisMock.mockReset()

  useExperienceTagsMock.mockReturnValue({
    tags: [
      { id: 1, name: "역사·문화" },
      { id: 2, name: "가족 활동" },
    ],
    loading: false,
  })
  fetchAnalysisMock.mockResolvedValue({ tripId: "trip-1", highConcentrationCount: 0, items: [] })
})

describe("RecommendationPurpose", () => {
  it("태그를 골라 '대안 찾기'를 누르면 searching 화면으로 선택한 태그를 들고 이동한다", async () => {
    const user = userEvent.setup()
    render(<RecommendationPurpose />)

    await user.click(screen.getByRole("button", { name: "역사·문화" }))
    await user.click(screen.getByRole("button", { name: "대안 찾기" }))

    expect(mockNavigate).toHaveBeenCalledWith("/trips/trip-1/places/tp-1/searching", {
      state: { purposeTagIds: [1] },
    })
  })

  it("건너뛰기를 누르면 태그 선택과 무관하게 빈 목록으로 이동한다", async () => {
    const user = userEvent.setup()
    render(<RecommendationPurpose />)

    await user.click(screen.getByRole("button", { name: "역사·문화" }))
    await user.click(screen.getByRole("button", { name: "건너뛰기" }))

    expect(mockNavigate).toHaveBeenCalledWith("/trips/trip-1/places/tp-1/searching", {
      state: { purposeTagIds: [] },
    })
  })

  it("AlternativeSearchLoading에서 돌아온 것이면(location.state.purposeTagIds) 그 태그가 이미 선택돼 있다", () => {
    // "다른 목적 선택하기"로 되돌아온 직후 이전에 고른 태그가 사라지면 안 된다(2026-09-19,
    // 코드 리뷰로 발견) — location.state로 넘어온 값이 초기 선택값으로 복원되는지 확인.
    mockLocationState = { purposeTagIds: [2] }
    render(<RecommendationPurpose />)

    expect(screen.getByRole("button", { name: "가족 활동" })).toHaveAttribute(
      "aria-pressed",
      "true",
    )
    expect(screen.getByRole("button", { name: "역사·문화" })).toHaveAttribute(
      "aria-pressed",
      "false",
    )
  })

  it("헤더의 뒤로가기는 navigate(-1)이 아니라 일정 점검 결과 화면으로 명시 이동한다", async () => {
    // "검색(후보없음)→목적 복원"을 거치면 방문 기록에 이 화면이 두 번 쌓일 수 있어(범위
    // 밖으로 남겨둔 문제) navigate(-1)이 어디로 갈지 예측하기 어렵다 — 그래서 이 화면의
    // 뒤로가기는 항상 점검 결과로 가도록 명시 경로를 쓰기로 정했다(2026-09-19).
    const user = userEvent.setup()
    render(<RecommendationPurpose />)

    await user.click(screen.getByRole("button", { name: "뒤로가기" }))

    expect(mockNavigate).toHaveBeenCalledWith("/trips/trip-1/remaining")
  })
})
