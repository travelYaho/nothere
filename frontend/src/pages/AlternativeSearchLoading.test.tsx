/**
 * AlternativeSearchLoading — 후보 0건(정상 결과)과 진짜 오류를 구분해서 보여주는지 확인한다.
 * STEP5의 인라인 검색 로직이 이 화면으로 옮겨오면서(2026-09-19, develop 병합), 이슈7에서
 * 확립한 원칙("후보 없음은 에러가 아니다, 같은 조건 재시도는 의미 없다")을 그대로 적용했다.
 */
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import AlternativeSearchLoading from "./AlternativeSearchLoading"

vi.mock("@/store/sessionStore", () => ({
  useSession: () => ({ session: { access_token: "test-token" }, user: null, isLoading: false }),
}))

const mockNavigate = vi.fn()
let mockLocationState: unknown = { purposeTagIds: [1] }
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
    useCreateRecommendationRequest: vi.fn(),
    scoreRoutes: vi.fn(),
  }
})

vi.mock("@/features/trips", () => ({ getTripDetail: vi.fn() }))

import { scoreRoutes, useCreateRecommendationRequest } from "@/features/recommendation"
import { getTripDetail } from "@/features/trips"

const useCreateRecommendationRequestMock = vi.mocked(useCreateRecommendationRequest)
const scoreRoutesMock = vi.mocked(scoreRoutes)
const getTripDetailMock = vi.mocked(getTripDetail)

beforeEach(() => {
  mockNavigate.mockReset()
  mockLocationState = { purposeTagIds: [1] }
  useCreateRecommendationRequestMock.mockReset()
  scoreRoutesMock.mockReset()
  getTripDetailMock.mockReset()
  getTripDetailMock.mockResolvedValue({ regionName: "부산광역시" } as never)
})

describe("AlternativeSearchLoading", () => {
  it("후보 0건이면 오류가 아니라 안내를 보여주고, compare로 이동하지 않는다", async () => {
    const create = vi.fn().mockResolvedValue({
      requestId: "req-1",
      tripPlaceId: "tp-1",
      searchMode: "default",
      status: "no_candidate",
      candidateCount: 0,
      excludedCount: 0,
    })
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })

    render(<AlternativeSearchLoading />)

    await waitFor(() => {
      expect(screen.getByText(/다른 목적을 선택해 주세요/)).toBeInTheDocument()
    })
    // 후보 없음은 role="alert"(빨간 오류) 대신 role="status"(중립 안내)로 보여야 한다.
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "다른 목적 선택하기" })).toBeInTheDocument()
    expect(mockNavigate).not.toHaveBeenCalledWith(expect.stringContaining("/compare"), expect.anything())
    expect(scoreRoutesMock).not.toHaveBeenCalled()
  })

  it("후보가 있으면 scoreRoutes까지 실행한 뒤 scored 상태로 compare 화면으로 대체 이동한다", async () => {
    const create = vi.fn().mockResolvedValue({
      requestId: "req-2",
      tripPlaceId: "tp-1",
      searchMode: "default",
      status: "success",
      candidateCount: 3,
      excludedCount: 0,
    })
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })
    scoreRoutesMock.mockResolvedValue({ requestId: "req-2", scoredCount: 3, candidates: [] })

    render(<AlternativeSearchLoading />)

    await waitFor(() => {
      expect(scoreRoutesMock).toHaveBeenCalledWith("test-token", "req-2")
    })
    expect(mockNavigate).toHaveBeenCalledWith(
      "/trips/trip-1/places/tp-1/compare?requestId=req-2",
      { state: { scored: true }, replace: true },
    )
  })

  it("실제 오류(예외)는 빨간 경고 + 다시 시도로 보여준다", async () => {
    const create = vi.fn().mockRejectedValue(new Error("서버 오류"))
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })

    render(<AlternativeSearchLoading />)

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("서버 오류")
    })
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument()
    expect(screen.queryByText(/다른 목적을 선택해 주세요/)).not.toBeInTheDocument()
  })

  it("'다른 목적 선택하기'를 누르면 목적 화면 경로로 지금 고른 태그를 들고 돌아간다(navigate(-1) 아님)", async () => {
    // navigate(-1)만 쓰면 이 화면에 직접 접근했을 때 목적 화면이 아닌 엉뚱한 곳으로 갈 수
    // 있고, 목적 화면이 다시 마운트될 때 태그를 복원할 방법도 없다(2026-09-19, 코드
    // 리뷰로 발견) — 그래서 명시적 경로 + state로 태그를 같이 넘기는지 직접 확인한다.
    const user = userEvent.setup()
    mockLocationState = { purposeTagIds: [1, 2] }
    const create = vi.fn().mockResolvedValue({
      requestId: "req-1",
      tripPlaceId: "tp-1",
      searchMode: "default",
      status: "no_candidate",
      candidateCount: 0,
      excludedCount: 0,
    })
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })

    render(<AlternativeSearchLoading />)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다른 목적 선택하기" })).toBeInTheDocument()
    })

    await user.click(screen.getByRole("button", { name: "다른 목적 선택하기" }))

    expect(mockNavigate).toHaveBeenCalledWith("/trips/trip-1/places/tp-1/purpose", {
      replace: true,
      state: { purposeTagIds: [1, 2] },
    })
  })

  it("헤더의 뒤로가기 화살표도 '다른 목적 선택하기'와 똑같이 태그를 들고 목적 화면으로 돌아간다", async () => {
    // onBack이 navigate(-1)로 남아있으면, 같은 화면에서 버튼 위치만 다를 뿐인 두 뒤로가기
    // 동작이 서로 달라진다(하나는 태그 보존, 하나는 유실) — 리뷰로 발견(2026-09-19).
    const user = userEvent.setup()
    mockLocationState = { purposeTagIds: [1, 2] }
    const create = vi.fn().mockResolvedValue({
      requestId: "req-1",
      tripPlaceId: "tp-1",
      searchMode: "default",
      status: "no_candidate",
      candidateCount: 0,
      excludedCount: 0,
    })
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })

    render(<AlternativeSearchLoading />)
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "다른 목적 선택하기" })).toBeInTheDocument()
    })

    await user.click(screen.getByRole("button", { name: "뒤로가기" }))

    expect(mockNavigate).toHaveBeenCalledWith("/trips/trip-1/places/tp-1/purpose", {
      replace: true,
      state: { purposeTagIds: [1, 2] },
    })
  })
})

describe("AlternativeSearchLoading 대기 문구", () => {
  it("대기 중에는 여행 문구를 보여주고, 일정의 지역을 한 번만 조회한다", async () => {
    const create = vi.fn().mockReturnValue(new Promise(() => {}))
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })

    render(<AlternativeSearchLoading />)

    await waitFor(() => expect(getTripDetailMock).toHaveBeenCalledWith("trip-1"))
    expect(getTripDetailMock).toHaveBeenCalledTimes(1)
    expect(document.body.textContent).toMatch(/심심풀이 퀴즈|여행 팁|알고 계셨나요\?/)
  })

  it("지역 조회가 실패해도 검색은 그대로 진행되고 화면 이동도 정상이다", async () => {
    getTripDetailMock.mockRejectedValue(new Error("401"))
    const create = vi.fn().mockResolvedValue({
      requestId: "req-3",
      tripPlaceId: "tp-1",
      searchMode: "default",
      status: "success",
      candidateCount: 2,
      excludedCount: 0,
    })
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })
    scoreRoutesMock.mockResolvedValue({ requestId: "req-3", scoredCount: 2, candidates: [] })

    render(<AlternativeSearchLoading />)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        "/trips/trip-1/places/tp-1/compare?requestId=req-3",
        { state: { scored: true }, replace: true },
      )
    })
  })

  it("오류로 끝나면 문구는 사라지고 오류 안내만 보인다", async () => {
    const create = vi.fn().mockRejectedValue(new Error("서버 오류"))
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })

    render(<AlternativeSearchLoading />)

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("서버 오류"))
    expect(document.body.textContent).not.toMatch(/심심풀이 퀴즈|여행 팁|알고 계셨나요\?/)
  })
})
