/**
 * CompareAlternatives의 "확인창·교체 방어" 검증 — 코드 추적으로만 확인했던 두 시나리오를
 * 실제 컴포넌트 렌더링으로 확인한다(2026-09-18, 코드 리뷰로 화면 테스트 보완 요청).
 */
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useMemo } from "react"
import CompareAlternatives from "./CompareAlternatives"
import { applyReplacement, keepTripPlace, useCompareFlow } from "@/features/recommendation"
import type { CompareCandidatesResponse } from "@/features/recommendation/types/part3"

vi.mock("@/store/sessionStore", () => ({
  useSession: () => ({ session: { access_token: "test-token" }, user: null, isLoading: false }),
}))

let mockRequestId: string | undefined = "req-1"
const mockNavigate = vi.fn()

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ tripId: "trip-1", tripPlaceId: "tp-1" }),
    useSearchParams: () => [
      new URLSearchParams(mockRequestId ? { requestId: mockRequestId } : {}),
      vi.fn(),
    ],
  }
})

vi.mock("@/features/recommendation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/recommendation")>()
  return {
    ...actual,
    useCompareFlow: vi.fn(),
    applyReplacement: vi.fn(),
    keepTripPlace: vi.fn(),
  }
})

const useCompareFlowMock = vi.mocked(useCompareFlow)
const applyReplacementMock = vi.mocked(applyReplacement)
const keepTripPlaceMock = vi.mocked(keepTripPlace)

function makeResponse(
  requestId: string,
  tripPlaceId: string,
  candidateId: string,
  isEligible = true,
): CompareCandidatesResponse {
  return {
    originalPlace: { placeId: "orig", name: "원래 장소", congestionLevel: "low" },
    candidates: [
      {
        candidateId,
        placeName: `후보-${candidateId}`,
        experienceScore: 0.8,
        routeScore: 0.7,
        congestionLevel: "low",
        congestionImprovement: "low_to_low",
        extraMinutes: 5,
        distancePrevM: 100,
        distanceNextM: 100,
        reasonText: null,
        isEligible,
        exclusionReason: null,
      },
    ],
    requestId,
    tripPlaceId,
  }
}

/** load()의 identity가 requestId가 바뀔 때만 새로 생기는 실제 훅의 계약을 그대로 흉내낸다 —
 * CompareAlternatives의 reset useEffect(dep: [load])가 정확히 이 성질에 의존하므로, mock도
 * 같은 성질을 지켜야 "요청 전환 시 reset" 시나리오를 제대로 재현할 수 있다. */
function installCompareFlowMock(getState: () => Partial<ReturnType<typeof useCompareFlowMock>>) {
  useCompareFlowMock.mockImplementation((requestId: string | undefined) => {
    const load = useMemo(() => vi.fn().mockResolvedValue(undefined), [requestId])
    return {
      data: null,
      loading: false,
      error: null,
      noCandidate: false,
      load,
      token: "test-token",
      ...getState(),
    }
  })
}

beforeEach(() => {
  mockRequestId = "req-1"
  mockNavigate.mockReset()
  applyReplacementMock.mockReset()
  keepTripPlaceMock.mockReset()
  useCompareFlowMock.mockReset()
})

describe("CompareAlternatives", () => {
  it("교체 확인창이 열린 상태에서 요청이 전환되면 확인창이 닫힌다", async () => {
    const user = userEvent.setup()
    let currentData: CompareCandidatesResponse | null = makeResponse("req-1", "tp-1", "c1")
    installCompareFlowMock(() => ({ data: currentData }))

    const { rerender } = render(<CompareAlternatives />)

    await waitFor(() => {
      expect(screen.getByText("이 장소로 변경")).toBeInTheDocument()
    })
    await user.click(screen.getByText("이 장소로 변경"))
    expect(screen.getByRole("alertdialog")).toBeInTheDocument()

    // 요청 전환: requestId가 바뀌면 useCompareFlow(requestId)가 새로운 load를 돌려주고,
    // CompareAlternatives의 reset effect가 pending/detail을 지운다.
    mockRequestId = "req-2"
    currentData = makeResponse("req-2", "tp-1", "c2")
    rerender(<CompareAlternatives />)

    await waitFor(() => {
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
    })
  })

  it("확인창을 연 뒤 결과가 다른 요청의 것으로 바뀌면, 교체를 눌러도 applyReplacement가 호출되지 않는다", async () => {
    const user = userEvent.setup()
    let currentData: CompareCandidatesResponse | null = makeResponse("req-1", "tp-1", "c1")
    installCompareFlowMock(() => ({ data: currentData }))

    const { rerender } = render(<CompareAlternatives />)

    await waitFor(() => {
      expect(screen.getByText("이 장소로 변경")).toBeInTheDocument()
    })
    await user.click(screen.getByText("이 장소로 변경"))
    expect(screen.getByRole("alertdialog")).toBeInTheDocument()

    // requestId는 그대로지만(= reset effect가 안 도는 경로), 결과 자체가 다른 요청의
    // 데이터로 바뀐 상황을 흉내낸다 — handleApply()의 방어적 검증이 이 경우를 잡아야 한다.
    currentData = makeResponse("other-req", "tp-1", "c1")
    rerender(<CompareAlternatives />)

    await user.click(screen.getByText("교체하기"))

    await waitFor(() => {
      expect(screen.getByText(/대안 목록이 갱신되었어요/)).toBeInTheDocument()
    })
    expect(applyReplacementMock).not.toHaveBeenCalled()
  })

  it("정상 상태에서는 교체하기를 누르면 applyReplacement가 실제로 호출된다(대조군)", async () => {
    const user = userEvent.setup()
    const data = makeResponse("req-1", "tp-1", "c1")
    installCompareFlowMock(() => ({ data }))
    applyReplacementMock.mockResolvedValue({
      replacementId: "r1",
      tripPlaceId: "tp-1",
      fromPlaceId: "orig",
      toPlaceId: "c1",
      resolutionStatus: "replaced",
      appliedAt: "2026-09-18T00:00:00Z",
    })

    render(<CompareAlternatives />)

    await waitFor(() => {
      expect(screen.getByText("이 장소로 변경")).toBeInTheDocument()
    })
    await user.click(screen.getByText("이 장소로 변경"))
    await user.click(screen.getByText("교체하기"))

    await waitFor(() => {
      expect(applyReplacementMock).toHaveBeenCalledWith("test-token", "tp-1", "c1")
    })
  })
})
