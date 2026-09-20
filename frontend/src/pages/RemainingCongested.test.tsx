/**
 * RemainingCongested(STEP4 결과 화면) — analysisStatus를 구분하지 않고 혼잡 장소 수가
 * 0이면 무조건 "모든 혼잡 장소를 확인했어요"라고 보여주던 문제(2026-09-19, 코드 리뷰로
 * 발견 — 전부 분석 실패여도 이 문구가 나왔다) 수정을 검증한다.
 */
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import RemainingCongested, { mergeAnalysisFields } from "./RemainingCongested"
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
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

beforeEach(() => {
  mockNavigate.mockReset()
  mockTripId = "trip-1"
  mockToken = "test-token"
  fetchAnalysisMock.mockReset()
  useRunAnalysisMock.mockReset()
  useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run: vi.fn() })
})

describe("mergeAnalysisFields — 경계 사례", () => {
  it("기존 목록이 빈 배열이고 새 응답에는 장소가 있으면, mismatchedIds가 비어 있어도 needsRefetch는 true다", () => {
    // 이전엔 "불일치 여부"를 mismatchedIds.length로만 판단해서, prevItems가 빈 배열이면
    // map 결과도 항상 빈 배열이라 "불일치 없음"으로 잘못 읽혀 재조회가 생략됐다(코드
    // 리뷰로 발견, 2026-09-19). needsRefetch를 별도 boolean으로 반환해야 이 경계를 잡는다.
    const fresh = [makeItem({ tripPlaceId: "tp-1", placeId: "place-A", placeName: "장소A" })]
    const { mismatchedIds, needsRefetch } = mergeAnalysisFields([], fresh)
    expect(mismatchedIds).toEqual([])
    expect(needsRefetch).toBe(true)
  })
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

  it("배경 재분석이 끝나기 전에도 목록을 먼저 보여준다 — 전체 화면을 '확인 중…'으로 가리지 않는다", async () => {
    // 예전엔 GET 완료 후에도 재분석(POST)까지 끝나야 loading이 꺼져서, 교체가 이미
    // 저장됐어도 사용자가 재분석 완료까지(약 23초) 기다려야 목록조차 볼 수 없었다
    // (코드 리뷰로 발견, 2026-09-19).
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({ tripPlaceId: "tp-1", placeName: "장소A", analysisStatus: "failed", level: null, analyzedAt: null }),
      ],
    })
    const runResult = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] }>()
    const run = vi.fn().mockReturnValue(runResult.promise)
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    render(<RemainingCongested />)

    // 목록은 재분석이 끝나기 전에 이미 보여야 한다.
    await waitFor(() => {
      expect(screen.getByText("장소A")).toBeInTheDocument()
    })
    expect(screen.queryByText("확인 중…")).not.toBeInTheDocument()
    // 이 카드는 아직 분석 중이므로 "혼잡도 확인 중"으로 표시되고, 실패 재시도 줄은 안 보인다.
    expect(screen.getByText("혼잡도 확인 중")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "다시 시도" })).not.toBeInTheDocument()

    // 재분석이 성공으로 끝나면 배지가 실제 결과로 갱신된다.
    runResult.resolve({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [makeItem({ tripPlaceId: "tp-1", placeName: "장소A", analysisStatus: "success", level: "low" })],
    })
    await waitFor(() => {
      expect(screen.queryByText("혼잡도 확인 중")).not.toBeInTheDocument()
    })
    expect(screen.getByText("모든 혼잡 장소를 확인했어요")).toBeInTheDocument()
  })

  it("A 트립의 재분석이 진행 중일 때 B로 넘어가면, A가 나중에 실패해도 B의 진행 상태·오류에 영향을 주지 않는다", async () => {
    // useRunAnalysis()의 loading/error는 훅 인스턴스 하나가 공유하는 상태라, 이 화면은
    // 그 값을 직접 읽지 않고 executionRef로 보호하는 로컬 상태(analyzingIds,
    // reanalysisError)만 사용해야 한다(코드 리뷰로 발견, 2026-09-19).
    mockTripId = "trip-1"
    fetchAnalysisMock.mockImplementation((_token: string, forTripId: string) => {
      if (forTripId === "trip-1") {
        return Promise.resolve({
          tripId: "trip-1",
          highConcentrationCount: 0,
          items: [
            makeItem({ tripPlaceId: "tp-a", placeName: "장소A", analysisStatus: "failed", level: null, analyzedAt: null }),
          ],
        })
      }
      return Promise.resolve({
        tripId: "trip-2",
        highConcentrationCount: 0,
        items: [makeItem({ tripPlaceId: "tp-b", placeName: "장소B", analysisStatus: "success", level: "low" })],
      })
    })
    const runResult = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] } | null>()
    const run = vi.fn().mockReturnValue(runResult.promise)
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    const { rerender } = render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByText("혼잡도 확인 중")).toBeInTheDocument()
    })

    // A의 재분석이 아직 끝나지 않은 채로 B로 이동한다. B는 이미 분석이 끝난 상태라
    // "확인 중"도, 안내 문구도 없어야 한다.
    mockTripId = "trip-2"
    rerender(<RemainingCongested />)
    await waitFor(() => {
      expect(screen.getByText("모든 혼잡 장소를 확인했어요")).toBeInTheDocument()
    })
    expect(screen.queryByText("혼잡도 확인 중")).not.toBeInTheDocument()

    // A의 재분석이 늦게 실패로 끝난다(run()이 내부에서 예외를 잡고 null을 반환하는 것과 동일).
    runResult.resolve(null)
    await new Promise((resolve) => setTimeout(resolve, 20))

    // B 화면은 그대로다 — A의 실패 안내가 B 화면에 새어나오면 안 된다.
    expect(screen.getByText("모든 혼잡 장소를 확인했어요")).toBeInTheDocument()
    expect(screen.queryByText(/실패했어요/)).not.toBeInTheDocument()
    expect(screen.queryByText("혼잡도 확인 중")).not.toBeInTheDocument()
  })

  it("첫 재분석이 실패해 '유지'를 누른 뒤 다시 분석하면, 그 응답이 로컬 변경(isFixed)을 덮지 않는다", async () => {
    // 배경 재분석은 이제(코드 리뷰로 점 ②를 반영해) 어떤 카드가 실제로 바뀔지 미리 알 수
    // 없어 전체 카드를 "확인 중"으로 표시하므로, 재분석이 진행 중인 동안에는 "유지" 버튼
    // 자체가 안 보인다 — 첫 재분석이 끝난(실패한) 뒤에 "유지"를 누르고, 이어서 두 번째
    // 재분석(다시 분석하기)이 그 변경을 덮지 않는지 확인한다. mergeAnalysisFields()가
    // 분석 관련 필드만 갱신하는지 검증한다(코드 리뷰로 발견, 2026-09-19).
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 1,
      items: [
        makeItem({
          tripPlaceId: "tp-1",
          placeName: "장소A",
          level: "high",
          analysisStatus: "success",
          resolutionStatus: "pending",
          isFixed: false,
        }),
        makeItem({
          tripPlaceId: "tp-2",
          placeName: "장소B",
          analysisStatus: "failed",
          level: null,
          analyzedAt: null,
        }),
      ],
    })
    let runResult = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] } | null>()
    const run = vi.fn().mockImplementation(() => runResult.promise)
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    const user = userEvent.setup()
    render(<RemainingCongested />)

    // 첫 재분석이 진행 중인 동안엔 "유지"가 안 보인다(전체 카드가 "확인 중"이라서).
    await waitFor(() => {
      expect(screen.getAllByText("혼잡도 확인 중").length).toBe(2)
    })
    expect(screen.queryByRole("button", { name: "유지" })).not.toBeInTheDocument()

    // 첫 재분석이 실패로 끝난다 — 목록은 그대로 남고(교체 전 상태), "다시 분석하기"가 뜬다.
    runResult.resolve(null)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다시 분석하기" })).toBeInTheDocument()
    })
    // 이제 tp-1은 analyzing이 아니므로 "유지"를 누를 수 있다.
    await user.click(screen.getByRole("button", { name: "유지" }))
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "유지" })).not.toBeInTheDocument()
    })

    // 두 번째 재분석("다시 분석하기")을 시작한다 — 이 응답의 tp-1은 "유지" 누르기 전
    // (isFixed:false) 시점을 반영하고 있다(백엔드 스냅샷이 그 사이 값을 못 본 상황을 흉내냄).
    runResult = deferred()
    await user.click(screen.getByRole("button", { name: "다시 분석하기" }))
    runResult.resolve({
      tripId: "trip-1",
      highConcentrationCount: 1,
      items: [
        makeItem({
          tripPlaceId: "tp-1",
          placeName: "장소A",
          level: "high",
          analysisStatus: "success",
          resolutionStatus: "pending",
          isFixed: false,
        }),
        makeItem({ tripPlaceId: "tp-2", placeName: "장소B", analysisStatus: "success", level: "low" }),
      ],
    })
    await waitFor(() => {
      expect(screen.queryByText("혼잡도 확인 중")).not.toBeInTheDocument()
    })

    // "유지" 버튼이 다시 나타나면 안 된다 — 두 번째 재분석 응답이 isFixed:true를 덮었다는 뜻이다.
    expect(screen.queryByRole("button", { name: "유지" })).not.toBeInTheDocument()
  })

  it("카드의 원래 상태가 'unavailable'이라 재시도 버튼이 없어도, 재분석 자체가 실패하면 일정 단위 '다시 분석하기'로 재시도할 수 있다", async () => {
    // 카드별 재시도 버튼은 analysisStatus==="failed"일 때만 있다 — "unavailable"로
    // 시작한 카드의 재분석 POST 자체가 실패하면(네트워크 오류 등), 카드에는 재시도 방법이
    // 전혀 없었다(코드 리뷰로 발견, 2026-09-19).
    fetchAnalysisMock.mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({
          tripPlaceId: "tp-1",
          placeName: "장소A",
          analysisStatus: "unavailable",
          level: null,
          analyzedAt: null,
        }),
      ],
    })
    const run = vi.fn().mockResolvedValue(null)
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다시 분석하기" })).toBeInTheDocument()
    })
    // 카드 자체에는 재시도 버튼이 없다 — analysisStatus가 "unavailable"이라서.
    expect(screen.queryByRole("button", { name: "다시 시도" })).not.toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(screen.getByRole("button", { name: "다시 분석하기" }))
    await waitFor(() => {
      expect(run).toHaveBeenCalledTimes(2)
    })
  })

  it("재분석 응답의 장소가 화면에 남아있는 장소와 다르면(placeId 불일치), 그 카드는 병합하지 않고 목록을 다시 조회한다", async () => {
    // mergeAnalysisFields()는 tripPlaceId로만 짝짓는다 — 다른 탭 등에서 같은 자리의
    // 장소가 그 사이 바뀌었다면(placeId가 달라짐) 재분석 응답의 혼잡도가 화면에 남은
    // 장소와 무관한 값일 수 있다(코드 리뷰로 발견, 2026-09-19).
    let getCall = 0
    fetchAnalysisMock.mockImplementation(() => {
      getCall += 1
      if (getCall === 1) {
        return Promise.resolve({
          tripId: "trip-1",
          highConcentrationCount: 0,
          items: [
            makeItem({
              tripPlaceId: "tp-1",
              placeId: "place-A",
              placeName: "장소A",
              analysisStatus: "failed",
              level: null,
              analyzedAt: null,
            }),
          ],
        })
      }
      // 재조회(refetch) — 실제로는 다른 장소(place-C)로 바뀐 최신 상태를 반영한다.
      return Promise.resolve({
        tripId: "trip-1",
        highConcentrationCount: 0,
        items: [
          makeItem({
            tripPlaceId: "tp-1",
            placeId: "place-C",
            placeName: "장소C",
            analysisStatus: "success",
            level: "low",
          }),
        ],
      })
    })
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        // 재분석 응답은 place-B(장소A와도, 최종 place-C와도 다른 placeId)를 담고 있다 —
        // 화면이 그 사이 알고 있던 place-A와 다르므로 병합 대상이 아니다.
        makeItem({
          tripPlaceId: "tp-1",
          placeId: "place-B",
          placeName: "장소B(응답)",
          analysisStatus: "success",
          level: "high",
        }),
      ],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    render(<RemainingCongested />)

    // 재분석 응답의 값(장소B, high)이 그대로 반영되면 안 되고, 재조회 결과(장소C)가 보여야 한다.
    await waitFor(() => {
      expect(screen.getByText("장소C")).toBeInTheDocument()
    })
    expect(screen.queryByText("장소B(응답)")).not.toBeInTheDocument()
    expect(fetchAnalysisMock).toHaveBeenCalledTimes(2)
  })

  it("placeId 불일치로 목록을 다시 조회하다 실패하면, 기존 목록은 유지한 채 오류 안내와 재조회 버튼을 보여준다", async () => {
    // 이전엔 이 재조회(fetchAnalysis)에 .catch()가 없어서, 실패하면 처리 안 된 Promise
    // 거부만 남고 화면은 "확인 중" 표시가 사라진 채 낡은 목록에 멈춰 있었다(코드 리뷰로
    // 발견, 2026-09-19). 실패해도 목록은 유지하고, 재분석(POST)이 아니라 GET만 다시
    // 시도하는 별도 버튼을 제공해야 한다.
    let getCall = 0
    fetchAnalysisMock.mockImplementation(() => {
      getCall += 1
      if (getCall === 1) {
        return Promise.resolve({
          tripId: "trip-1",
          highConcentrationCount: 0,
          items: [
            makeItem({
              tripPlaceId: "tp-1",
              placeId: "place-A",
              placeName: "장소A",
              analysisStatus: "failed",
              level: null,
              analyzedAt: null,
            }),
          ],
        })
      }
      // 재조회 시도(2번째 GET)는 실패한다.
      return Promise.reject(new Error("네트워크 오류"))
    })
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({
          tripPlaceId: "tp-1",
          placeId: "place-B",
          placeName: "장소B(응답)",
          analysisStatus: "success",
          level: "low",
        }),
      ],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    render(<RemainingCongested />)

    // 재조회 실패 안내와 "다시 조회하기" 버튼이 뜨고, 기존 목록(장소A)은 그대로 남는다.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다시 조회하기" })).toBeInTheDocument()
    })
    expect(screen.getByText("네트워크 오류")).toBeInTheDocument()
    expect(screen.getByText("장소A")).toBeInTheDocument()
    expect(screen.queryByText("혼잡도 확인 중")).not.toBeInTheDocument()

    // "다시 조회하기"는 재분석(POST)이 아니라 GET만 다시 시도한다.
    expect(run).toHaveBeenCalledTimes(1)
    expect(fetchAnalysisMock).toHaveBeenCalledTimes(2)
  })

  it("재조회가 진행 중일 때는 '확인하고 있어요' 문구를 보여주고, 실패해야만 '다시 조회하기' 안내로 바뀐다", async () => {
    // "다시 조회하기" 버튼은 refetchError가 있을 때만(즉 실패했을 때만) 렌더링된다 —
    // 진행 중에 그 버튼을 안내하면 화면에 없는 버튼을 가리키는 셈이라 어긋난다(코드
    // 리뷰로 발견, 2026-09-19).
    fetchAnalysisMock.mockResolvedValueOnce({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({
          tripPlaceId: "tp-1",
          placeId: "place-A",
          placeName: "장소A",
          analysisStatus: "failed",
          level: null,
          analyzedAt: null,
        }),
      ],
    })
    const refetchDeferred = deferred<{ tripId: string; highConcentrationCount: number; items: AnalysisItem[] }>()
    fetchAnalysisMock.mockImplementationOnce(() => refetchDeferred.promise)
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({
          tripPlaceId: "tp-1",
          placeId: "place-B",
          placeName: "장소B(응답)",
          analysisStatus: "success",
          level: "low",
        }),
      ],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    render(<RemainingCongested />)

    // 재조회(두 번째 GET)가 아직 응답하지 않은 상태 — 진행 중 문구여야 하고, 버튼은 없다.
    await waitFor(() => {
      expect(screen.getByText("최신 일정을 확인하고 있어요")).toBeInTheDocument()
    })
    expect(screen.queryByText("아래에서 최신 일정을 다시 조회할 수 있어요")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "다시 조회하기" })).not.toBeInTheDocument()

    // 재조회가 실패로 끝나면 그제서야 "다시 조회하기" 안내·버튼으로 바뀐다.
    refetchDeferred.reject(new Error("네트워크 오류"))
    await waitFor(() => {
      expect(screen.getByText("아래에서 최신 일정을 다시 조회할 수 있어요")).toBeInTheDocument()
    })
    expect(screen.queryByText("최신 일정을 확인하고 있어요")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "다시 조회하기" })).toBeInTheDocument()
  })

  it("일부 카드만 placeId가 불일치할 때, 불일치 없이 정상 병합된 다른 카드는 재조회가 실패해도 '확인 중'에 갇히지 않는다", async () => {
    // runBackgroundAnalysis()가 시작할 때 currentItems 전체를 analyzingIds에 넣는데,
    // needsRefetch 분기에서 그 집합을 비우지 않고 곧장 refetchList(mismatchedIds)를 부르면
    // — refetchList의 analyzingIds 갱신은 더하기만 하므로 — 불일치 없는 카드가 analyzingIds에
    // 계속 남는다. 재조회가 실패하면 catch가 mismatchedIds만 빼서, 그 정상 카드는 영영
    // "확인 중"에 갇힌다(코드 리뷰로 발견, 2026-09-19).
    let getCall = 0
    fetchAnalysisMock.mockImplementation(() => {
      getCall += 1
      if (getCall === 1) {
        return Promise.resolve({
          tripId: "trip-1",
          highConcentrationCount: 0,
          items: [
            makeItem({
              tripPlaceId: "tp-1",
              placeId: "place-A",
              placeName: "장소A",
              analysisStatus: "failed",
              level: null,
              analyzedAt: null,
            }),
            makeItem({
              tripPlaceId: "tp-2",
              placeId: "place-C",
              placeName: "장소C",
              analysisStatus: "failed",
              level: null,
              analyzedAt: null,
            }),
          ],
        })
      }
      // 재조회(2번째 GET, mismatchedIds만 대상)는 실패한다.
      return Promise.reject(new Error("네트워크 오류"))
    })
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        // tp-1: placeId가 달라져 불일치(재조회 대상).
        makeItem({
          tripPlaceId: "tp-1",
          placeId: "place-B",
          placeName: "장소B(응답)",
          analysisStatus: "success",
          level: "low",
        }),
        // tp-2: placeId가 그대로라 정상 병합된다(재조회 대상 아님).
        makeItem({
          tripPlaceId: "tp-2",
          placeId: "place-C",
          placeName: "장소C",
          analysisStatus: "success",
          level: "low",
        }),
      ],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    render(<RemainingCongested />)

    // 재조회(불일치 카드만 대상)가 실패로 끝날 때까지 기다린다.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다시 조회하기" })).toBeInTheDocument()
    })

    // 재조회가 끝난 뒤에는 어떤 카드도 "확인 중"이면 안 된다 — tp-1(불일치)은 실패로
    // "최신 정보 확인 필요"가 되고, tp-2(불일치 없음)는 이미 병합이 끝나 정상 상태여야
    // 한다. 버그가 있으면 tp-2가 analyzingIds에 남아 이 텍스트가 계속 보인다.
    expect(screen.queryByText("혼잡도 확인 중")).not.toBeInTheDocument()
    expect(screen.getByText("장소C")).toBeInTheDocument()
  })

  it("placeId 불일치로 재조회가 실패하면, '확인 중' 표시는 꺼져도 그 카드의 등급·대안보기·유지는 계속 숨겨진다", async () => {
    // 재조회 실패 시 analyzingIds에서만 빼면 낡은 장소의 등급·행동 버튼이 다시 나타난다
    // (코드 리뷰로 발견, 2026-09-19) — 화면엔 교체 전 장소(장소A, high)가 보이는데 "유지"를
    // 누르면 tripPlaceId 기준으로 서버는 이미 교체된 다른 장소를 고정 처리할 수 있었다.
    // stale 표시가 남아 성공적으로 재조회하기 전까지 행동 버튼을 계속 막는지 확인한다.
    let getCall = 0
    fetchAnalysisMock.mockImplementation(() => {
      getCall += 1
      if (getCall === 1) {
        return Promise.resolve({
          tripId: "trip-1",
          highConcentrationCount: 1,
          items: [
            makeItem({
              tripPlaceId: "tp-1",
              placeId: "place-A",
              placeName: "장소A",
              analysisStatus: "success",
              level: "high",
              resolutionStatus: "pending",
              isFixed: false,
              analyzedAt: null,
            }),
          ],
        })
      }
      return Promise.reject(new Error("네트워크 오류"))
    })
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({
          tripPlaceId: "tp-1",
          placeId: "place-B",
          placeName: "장소B(응답)",
          analysisStatus: "success",
          level: "low",
        }),
      ],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다시 조회하기" })).toBeInTheDocument()
    })

    // "확인 중" 진행 표시는 꺼졌지만, 낡은 장소의 등급·행동 버튼은 여전히 안 보여야 한다.
    expect(screen.queryByText("혼잡도 확인 중")).not.toBeInTheDocument()
    expect(screen.getByText("최신 정보 확인 필요")).toBeInTheDocument()
    expect(screen.queryByText("혼잡 가능성 높음")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "대안 보기" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "유지" })).not.toBeInTheDocument()

    // 상단 요약도 카드와 같은 기준을 써야 한다 — stale 카드는 원래 등급이 "high"였지만
    // crowdedCount에서 빠져서 "남은 혼잡 1곳"이 아니라 "최신 일정 확인이 필요한 장소"로
    // 보여야 한다(코드 리뷰로 발견, 2026-09-19 — 카드와 상단 안내가 모순될 수 있었다).
    expect(screen.getByText("최신 일정 확인이 필요한 장소 1곳")).toBeInTheDocument()
    expect(screen.queryByText("남은 혼잡 1곳")).not.toBeInTheDocument()
  })

  it("A 트립에서 재조회 오류가 남은 채로 B 트립으로 넘어가면, B 화면에는 그 오류가 보이지 않는다", async () => {
    // reanalysisError는 새 조회 effect가 시작될 때 지웠지만 refetchError는 빠져 있었다
    // (코드 리뷰로 발견, 2026-09-19) — A에서 재조회 실패 오류가 뜬 채로 B로 넘어가면 B
    // 화면에도 그 오류가 그대로 보였다.
    mockTripId = "trip-1"
    let getCallForTrip1 = 0
    fetchAnalysisMock.mockImplementation((_token: string, forTripId: string) => {
      if (forTripId === "trip-1") {
        getCallForTrip1 += 1
        if (getCallForTrip1 === 1) {
          return Promise.resolve({
            tripId: "trip-1",
            highConcentrationCount: 0,
            items: [
              makeItem({
                tripPlaceId: "tp-a",
                placeId: "place-A",
                placeName: "장소A",
                analysisStatus: "failed",
                level: null,
                analyzedAt: null,
              }),
            ],
          })
        }
        // 재조회(2번째 GET)는 실패한다.
        return Promise.reject(new Error("네트워크 오류"))
      }
      return Promise.resolve({
        tripId: "trip-2",
        highConcentrationCount: 0,
        items: [makeItem({ tripPlaceId: "tp-b", placeName: "장소B", analysisStatus: "success", level: "low" })],
      })
    })
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({
          tripPlaceId: "tp-a",
          placeId: "place-Z",
          placeName: "장소Z(응답)",
          analysisStatus: "success",
          level: "low",
        }),
      ],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    const { rerender } = render(<RemainingCongested />)

    // trip-1에서 재조회 실패 오류가 뜬다(placeId 불일치 → 재조회 → 실패).
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다시 조회하기" })).toBeInTheDocument()
    })

    // B로 넘어간다.
    mockTripId = "trip-2"
    rerender(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByText("장소B")).toBeInTheDocument()
    })
    expect(screen.queryByRole("button", { name: "다시 조회하기" })).not.toBeInTheDocument()
    expect(screen.queryByText("네트워크 오류")).not.toBeInTheDocument()
  })

  it("기존 등급이 low였던 카드가 stale이 된 뒤 재조회에 실패해도, '모든 혼잡 장소를 확인했어요'가 나오지 않는다", async () => {
    // stale 카드가 crowdedCount/failedCount/unavailableCount 어디에도 안 걸리면(원래
    // low였으니까) 다른 집계도 전부 0이 돼서, 상단은 "완료" 문구로 떨어진다 — 정작 이
    // 카드 하나는 최신 상태를 확인 못 한 채로 남아 있는데도(코드 리뷰로 발견, 2026-09-19).
    let getCall = 0
    fetchAnalysisMock.mockImplementation(() => {
      getCall += 1
      if (getCall === 1) {
        return Promise.resolve({
          tripId: "trip-1",
          highConcentrationCount: 0,
          items: [
            makeItem({
              tripPlaceId: "tp-1",
              placeId: "place-A",
              placeName: "장소A",
              analysisStatus: "success",
              level: "low",
              analyzedAt: null,
            }),
          ],
        })
      }
      return Promise.reject(new Error("네트워크 오류"))
    })
    const run = vi.fn().mockResolvedValue({
      tripId: "trip-1",
      highConcentrationCount: 0,
      items: [
        makeItem({
          tripPlaceId: "tp-1",
          placeId: "place-B",
          placeName: "장소B(응답)",
          analysisStatus: "success",
          level: "low",
        }),
      ],
    })
    useRunAnalysisMock.mockReturnValue({ data: null, loading: false, error: null, run })

    render(<RemainingCongested />)

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다시 조회하기" })).toBeInTheDocument()
    })

    expect(screen.getByText("최신 일정 확인이 필요한 장소 1곳")).toBeInTheDocument()
    expect(screen.queryByText("모든 혼잡 장소를 확인했어요")).not.toBeInTheDocument()
  })
})
