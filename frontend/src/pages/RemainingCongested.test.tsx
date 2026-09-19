/**
 * RemainingCongested(STEP4 결과 화면) — analysisStatus를 구분하지 않고 혼잡 장소 수가
 * 0이면 무조건 "모든 혼잡 장소를 확인했어요"라고 보여주던 문제(2026-09-19, 코드 리뷰로
 * 발견 — 전부 분석 실패여도 이 문구가 나왔다) 수정을 검증한다.
 */
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import RemainingCongested from "./RemainingCongested"
import type { AnalysisItem } from "@/features/recommendation"

vi.mock("@/store/sessionStore", () => ({
  useSession: () => ({ session: { access_token: "test-token" }, user: null, isLoading: false }),
}))

const mockNavigate = vi.fn()
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ tripId: "trip-1" }),
    useLocation: () => ({ state: null, pathname: "/trips/trip-1/remaining", search: "", hash: "", key: "test" }),
  }
})

vi.mock("@/features/recommendation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/recommendation")>()
  return {
    ...actual,
    fetchAnalysis: vi.fn(),
    keepTripPlace: vi.fn(),
    useAccessToken: () => "test-token",
    useRunAnalysis: vi.fn(),
  }
})

import { fetchAnalysis, useRunAnalysis } from "@/features/recommendation"

const fetchAnalysisMock = vi.mocked(fetchAnalysis)
const useRunAnalysisMock = vi.mocked(useRunAnalysis)

function makeItem(overrides: Partial<AnalysisItem>): AnalysisItem {
  return {
    tripPlaceId: "tp-1",
    placeId: "place-1",
    placeName: "경국사",
    analysisStatus: "success",
    level: "low",
    unknownReason: null,
    ruleVersion: "v1",
    isFixed: false,
    resolutionStatus: "pending",
    canRecommendAlternative: true,
    analyzedAt: "2026-09-19T00:00:00Z",
    visitTime: "10:00",
    ...overrides,
  }
}

beforeEach(() => {
  mockNavigate.mockReset()
  fetchAnalysisMock.mockReset()
  useRunAnalysisMock.mockReset()
  useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run: vi.fn() })
})

describe("RemainingCongested", () => {
  it("모든 장소의 분석이 실패했으면(혼잡 0건) '모든 혼잡 장소를 확인했어요' 대신 '분석하지 못한 장소'로 구분해 보여준다", async () => {
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({ tripPlaceId: "tp-1", analysisStatus: "failed", level: null }),
        makeItem({ tripPlaceId: "tp-2", analysisStatus: "unavailable", level: null }),
      ],
    })

    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByText("분석하지 못한 장소 2곳")).toBeInTheDocument()
    })
    expect(screen.queryByText("모든 혼잡 장소를 확인했어요")).not.toBeInTheDocument()
  })

  it("실제로 모든 장소가 정상 분석되고 혼잡한 곳이 없으면 기존 문구를 그대로 보여준다(대조군)", async () => {
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ analysisStatus: "success", level: "low" })],
    })

    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByText("모든 혼잡 장소를 확인했어요")).toBeInTheDocument()
    })
    expect(screen.queryByText(/분석하지 못한 장소/)).not.toBeInTheDocument()
  })

  it("분석 실패 카드에는 '다시 시도' 버튼이 있고, 누르면 재분석을 요청해 결과를 갱신한다", async () => {
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ tripPlaceId: "tp-1", analysisStatus: "failed", level: null })],
    })
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ tripPlaceId: "tp-1", analysisStatus: "success", level: "low" })],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    const user = userEvent.setup()
    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument()
    })

    await user.click(screen.getByRole("button", { name: "다시 시도" }))

    expect(run).toHaveBeenCalledTimes(1)
    await waitFor(() => {
      expect(screen.getByText("모든 혼잡 장소를 확인했어요")).toBeInTheDocument()
    })
  })

  it("정상 분석된(성공) 장소 카드에는 '다시 시도' 버튼이 없다(대조군)", async () => {
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ analysisStatus: "success", level: "low" })],
    })

    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByText("모든 혼잡 장소를 확인했어요")).toBeInTheDocument()
    })
    expect(screen.queryByRole("button", { name: "다시 시도" })).not.toBeInTheDocument()
  })

  it("실패(failed)는 없고 정보 부족(unavailable)만 있으면 '다시 시도' 안내 대신 정보 부족 안내를 보여주고, 재시도 버튼 자체가 없다", async () => {
    // 재시도 버튼은 analysisStatus==="failed" 카드에만 있다 — unavailable(지역코드 없음
    // 등)은 재시도해도 결과가 안 바뀌므로 버튼이 없다. 예전 코드는 failed/unavailable을
    // 묶어서 세면서 안내 문구는 항상 "아래 카드에서 다시 시도할 수 있어요"였다 — 버튼 없는
    // 화면에 재시도를 안내하는 불일치가 있었다(코드 리뷰로 발견, 2026-09-19).
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ tripPlaceId: "tp-1", analysisStatus: "unavailable", level: null })],
    })

    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByText("분석하지 못한 장소 1곳")).toBeInTheDocument()
    })
    expect(screen.getByText("일부 장소는 혼잡도 정보를 제공하지 못해요")).toBeInTheDocument()
    expect(screen.queryByText("아래 카드에서 다시 시도할 수 있어요")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "다시 시도" })).not.toBeInTheDocument()
  })

  it("혼잡한 장소와 분석 실패 장소가 함께 있으면, 혼잡 개수와 별개로 분석하지 못한 장소 개수도 보여준다", async () => {
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 1,
      items: [
        makeItem({ tripPlaceId: "tp-1", analysisStatus: "success", level: "high" }),
        makeItem({ tripPlaceId: "tp-2", analysisStatus: "failed", level: null }),
      ],
    })

    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByText("남은 혼잡 1곳")).toBeInTheDocument()
    })
    expect(screen.getByText(/분석하지 못한 장소 1곳/)).toBeInTheDocument()
  })

  it("이미 '유지'로 고정한 장소라도 분석이 실패했으면(예: 일정 변경으로 재분석되며 API가 실패) 여전히 분석 실패로 집계하고 재시도 버튼을 보여준다", async () => {
    // isFixed는 "사용자가 이 장소를 그대로 쓰기로 했다"는 뜻일 뿐, "분석이 성공했다"는
    // 뜻이 아니다 — 예전 코드는 isFixed인 장소를 실패 집계에서 빼서, 한 번도 성공적으로
    // 분석되지 못한 장소가 조용히 "처리 완료"로 묻혔다(코드 리뷰로 발견, 2026-09-19).
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({
          tripPlaceId: "tp-1",
          analysisStatus: "failed",
          level: null,
          isFixed: true,
          resolutionStatus: "pending",
        }),
      ],
    })

    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByText("분석하지 못한 장소 1곳")).toBeInTheDocument()
    })
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument()
  })
})
