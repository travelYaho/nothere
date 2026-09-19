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
// let 변수로 둔다 — 트립 전환(재실행) 시나리오 테스트에서 rerender 사이에 tripId를 바꿔
// effect 의존성 변경을 실제로 유발해야 한다.
let mockTripId = "trip-1"
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ tripId: mockTripId }),
    useLocation: () => ({ state: null, pathname: "/trips/trip-1/remaining", search: "", hash: "", key: "test" }),
  }
})

// let 변수로 둔다 — 토큰 변경으로 effect가 재실행되는 시나리오(같은 tripId, 다른 token)를
// 테스트에서 재현해야 한다.
let mockToken = "test-token"
vi.mock("@/features/recommendation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/recommendation")>()
  return {
    ...actual,
    fetchAnalysis: vi.fn(),
    keepTripPlace: vi.fn(),
    useAccessToken: () => mockToken,
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

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })
  return { promise, resolve }
}

beforeEach(() => {
  mockNavigate.mockReset()
  mockTripId = "trip-1"
  mockToken = "test-token"
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

  it("이전 트립의 조회가 아직 끝나지 않은 채로 새 트립으로 넘어가면, 뒤처진(낡은) 실행은 재분석 POST(runAnalysis)를 시작하지 않는다", async () => {
    // 실사용 로그에서 같은 지역 집중률 조회가 거의 동시에 두 번 도는 게 확인됐다(2026-09-19,
    // 코드 리뷰) — effect가 두 번 걸려도 예전 코드는 cancelled 플래그가 "결과를 반영할지"만
    // 막고 runAnalysis() 시작 자체는 못 막았다. 트립 전환(tripId 변경)으로 이 effect가
    // 다시 걸리는 상황을 그대로 재현해서, 낡은 실행이 fetchAnalysis 응답을 늦게 받아도
    // runAnalysis()를 부르지 않는지 확인한다.
    const first = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] }>()
    const second = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] }>()
    let call = 0
    fetchAnalysisMock.mockImplementation(() => {
      call += 1
      return call === 1 ? first.promise : second.promise
    })
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-2",
      highConcentrationCount: 0,
      items: [makeItem({ tripPlaceId: "tp-2", analysisStatus: "success", level: "low" })],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    const { rerender } = render(<RemainingCongested />)

    // 트립 전환 — 첫 번째 fetchAnalysis가 아직 응답하지 않은 상태에서 tripId가 바뀐다.
    mockTripId = "trip-2"
    rerender(<RemainingCongested />)
    await waitFor(() => {
      expect(fetchAnalysisMock).toHaveBeenCalledTimes(2)
    })

    // 낡은(첫 번째) 응답이 늦게 도착한다 — 분석이 비어 있어(analyzedAt null) 재분석이
    // 필요한 것처럼 보이는 응답이지만, 이 실행은 이미 낡았으므로 runAnalysis()를 부르면 안 된다.
    first.resolve({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ tripPlaceId: "tp-1", analysisStatus: "failed", level: null, analyzedAt: null })],
    })
    // 마이크로태스크를 흘려보낸 뒤에도 run이 호출되지 않았는지 확인.
    await Promise.resolve()
    await Promise.resolve()
    expect(run).not.toHaveBeenCalled()

    // 최신(두 번째) 응답이 도착하면 정상적으로 재분석이 걸린다.
    second.resolve({
      tripId: "trip-2",
      highConcentrationCount: 0,
      items: [makeItem({ tripPlaceId: "tp-2", analysisStatus: "failed", level: null, analyzedAt: null })],
    })
    await waitFor(() => {
      expect(run).toHaveBeenCalledTimes(1)
    })
  })

  it("분석 GET 응답을 기다리는 도중 화면을 완전히 벗어나면(언마운트), 응답이 늦게 도착해도 재분석 POST를 시작하지 않는다", async () => {
    // 처음 버전은 실행 번호를 "새 실행이 시작될 때만" 올렸다 — 언마운트는 새 실행이
    // 아니라서 번호가 그대로 남고, 늦게 도착한 GET 응답이 재분석 필요 상태로 보이면
    // 그대로 runAnalysis()를 불렀다(2차 코드 리뷰로 발견). effect cleanup에서도 번호를
    // 올려 무효화해야 한다.
    const first = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] }>()
    fetchAnalysisMock.mockImplementation(() => first.promise)
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ analysisStatus: "success", level: "low" })],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    const { unmount } = render(<RemainingCongested />)
    await waitFor(() => {
      expect(fetchAnalysisMock).toHaveBeenCalledTimes(1)
    })

    unmount()

    first.resolve({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ analysisStatus: "failed", level: null, analyzedAt: null })],
    })
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
    expect(run).not.toHaveBeenCalled()
  })

  it("같은 트립에 대해 재분석이 이미 진행 중일 때 effect가 다시 걸려도(예: 토큰 갱신), 재분석 POST를 한 번만 보내고 그 결과를 나눠 쓴다", async () => {
    // A가 runAnalysis()를 await하는 도중에는 이미 되돌릴 수 없이 요청을 보낸 뒤라,
    // 실행 번호만으로는 뒤이은 B가 같은 트립에 또 요청을 보내는 걸 못 막는다(2차 코드
    // 리뷰로 발견). tripId별로 "지금 진행 중인 Promise"를 나눠 쓰는지 확인한다.
    mockTripId = "trip-1"
    const firstGet = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] }>()
    const secondGet = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] }>()
    let getCall = 0
    fetchAnalysisMock.mockImplementation(() => {
      getCall += 1
      return getCall === 1 ? firstGet.promise : secondGet.promise
    })
    const runResult = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] }>()
    const run = vi.fn().mockReturnValue(runResult.promise)
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    const { rerender } = render(<RemainingCongested />)

    firstGet.resolve({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ analysisStatus: "failed", level: null, analyzedAt: null })],
    })
    await waitFor(() => {
      expect(run).toHaveBeenCalledTimes(1)
    })

    // 같은 트립인데 토큰이 바뀌어(예: 세션 갱신) effect가 다시 걸린다 — 첫 번째 재분석은
    // 아직 진행 중(runResult 미해결)이다.
    mockToken = "test-token-2"
    rerender(<RemainingCongested />)
    await waitFor(() => {
      expect(fetchAnalysisMock).toHaveBeenCalledTimes(2)
    })

    secondGet.resolve({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ analysisStatus: "failed", level: null, analyzedAt: null })],
    })
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
    // 두 번째 실행도 재분석이 필요하다고 판단했지만, 첫 번째가 이미 진행 중이므로 새 POST를
    // 또 보내면 안 된다.
    expect(run).toHaveBeenCalledTimes(1)

    runResult.resolve({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ analysisStatus: "success", level: "low" })],
    })
    await waitFor(() => {
      expect(screen.getByText("모든 혼잡 장소를 확인했어요")).toBeInTheDocument()
    })
  })

  it("A에서 수동 '다시 시도'를 누른 뒤 B로 넘어가면, A의 응답이 늦게 도착해도 B 화면을 덮어쓰지 않는다", async () => {
    // 자동 조회 effect는 executionRef로 이 경쟁을 이미 막지만, handleRetry(수동 "다시
    // 시도")에는 그 검사가 없었다(코드 리뷰로 발견, 2026-09-19) — A에서 재시도를 누른 뒤
    // 응답이 오기 전에 B로 넘어가면, 늦게 온 A의 결과가 setItems로 B 화면을 덮어썼다.
    mockTripId = "trip-1"
    fetchAnalysisMock.mockImplementation((_token: string, forTripId: string) => {
      if (forTripId === "trip-1") {
        return Promise.resolve({
          tripId: "trip-1",
          highConcentrationCount: 0,
          items: [
            makeItem({ tripPlaceId: "tp-a", placeName: "장소A", analysisStatus: "failed", level: null }),
          ],
        })
      }
      return Promise.resolve({
        tripId: "trip-2",
        highConcentrationCount: 0,
        items: [
          makeItem({ tripPlaceId: "tp-b", placeName: "장소B", analysisStatus: "success", level: "low" }),
        ],
      })
    })
    const retryResult = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] }>()
    const run = vi.fn().mockReturnValue(retryResult.promise)
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    const user = userEvent.setup()
    const { rerender } = render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByText("장소A")).toBeInTheDocument()
    })

    await user.click(screen.getByRole("button", { name: "다시 시도" }))
    expect(run).toHaveBeenCalledTimes(1)

    // A의 재시도가 아직 끝나지 않은 채로 B로 이동한다.
    mockTripId = "trip-2"
    rerender(<RemainingCongested />)
    await waitFor(() => {
      expect(screen.getByText("장소B")).toBeInTheDocument()
    })

    // A의 재시도 응답이 늦게 도착한다. handleRetry 내부에서 startAnalysisIfNeeded()의
    // .finally()까지 거쳐야 하므로, Promise.resolve()를 몇 번 거는 것보다 실제
    // setTimeout(0)으로 마이크로태스크 큐 전체를 확실히 비운다.
    retryResult.resolve({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ tripPlaceId: "tp-a", placeName: "장소A", analysisStatus: "success", level: "low" })],
    })
    await new Promise((resolve) => setTimeout(resolve, 20))

    // B 화면이 그대로 유지돼야 한다 — A의 데이터로 덮어써지면 안 된다.
    expect(screen.getByText("장소B")).toBeInTheDocument()
    expect(screen.queryByText("장소A")).not.toBeInTheDocument()
  })
})
