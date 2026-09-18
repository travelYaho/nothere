/**
 * RecommendationPurpose(STEP5)의 후보 0건 처리 검증 — "같은 조건으로 다시 찾기" 버튼을
 * 없애고 "다른 목적을 선택해 주세요" 안내로 바꾼 수정을 실제 렌더링으로 확인한다
 * (2026-09-18, 코드 리뷰로 "같은 조건 재시도는 반경이 이미 자동 확대돼 의미가 없다"는
 * 지적을 받아 UX를 변경).
 */
import { act, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useCallback, useState } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import RecommendationPurpose from "./RecommendationPurpose"

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((res) => {
    resolve = res
  })
  return { promise, resolve }
}

vi.mock("@/store/sessionStore", () => ({
  useSession: () => ({ session: { access_token: "test-token" }, user: null, isLoading: false }),
}))

const mockNavigate = vi.fn()
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ tripId: "trip-1", tripPlaceId: "tp-1" }),
  }
})

vi.mock("@/features/recommendation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/recommendation")>()
  return {
    ...actual,
    useExperienceTags: vi.fn(),
    useCreateRecommendationRequest: vi.fn(),
    fetchAnalysis: vi.fn(),
  }
})

import {
  fetchAnalysis,
  useCreateRecommendationRequest,
  useExperienceTags,
} from "@/features/recommendation"

const useExperienceTagsMock = vi.mocked(useExperienceTags)
const useCreateRecommendationRequestMock = vi.mocked(useCreateRecommendationRequest)
const fetchAnalysisMock = vi.mocked(fetchAnalysis)

beforeEach(() => {
  mockNavigate.mockReset()
  useExperienceTagsMock.mockReset()
  useCreateRecommendationRequestMock.mockReset()
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
  it("후보 0건 응답이면 compare로 이동하지 않고, 재시도 버튼 없이 안내와 돌아가기만 보여준다", async () => {
    const user = userEvent.setup()
    const create = vi.fn().mockResolvedValue({
      requestId: "req-1",
      tripPlaceId: "tp-1",
      searchMode: "default",
      status: "no_candidate",
      candidateCount: 0,
      excludedCount: 0,
    })
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })

    render(<RecommendationPurpose />)

    await user.click(screen.getByRole("button", { name: "대안 찾기" }))

    await waitFor(() => {
      expect(screen.getByText(/다른 목적을 선택해 주세요/)).toBeInTheDocument()
    })
    // "같은 조건으로 다시 찾기"류의 재시도 버튼은 없어야 한다 — 같은 태그로 다시 요청해도
    // 반경 확대가 이미 이번 요청 안에서 다 시도된 뒤라 결과가 똑같다(리뷰로 발견).
    expect(screen.queryByText(/같은 조건으로 다시 찾기/)).not.toBeInTheDocument()
    expect(screen.getByText("점검 결과로 돌아가기")).toBeInTheDocument()
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it("후보가 있으면 compare 화면으로 이동한다(대조군)", async () => {
    const user = userEvent.setup()
    const create = vi.fn().mockResolvedValue({
      requestId: "req-2",
      tripPlaceId: "tp-1",
      searchMode: "default",
      status: "success",
      candidateCount: 3,
      excludedCount: 0,
    })
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })

    render(<RecommendationPurpose />)
    await user.click(screen.getByRole("button", { name: "대안 찾기" }))

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        "/trips/trip-1/places/tp-1/compare?requestId=req-2",
      )
    })
  })

  it("후보 0건 안내가 뜬 뒤 태그를 바꾸면 안내가 사라지고 '대안 찾기' 버튼이 다시 나타난다", async () => {
    const user = userEvent.setup()
    const create = vi.fn().mockResolvedValue({
      requestId: "req-1",
      tripPlaceId: "tp-1",
      searchMode: "default",
      status: "no_candidate",
      candidateCount: 0,
      excludedCount: 0,
    })
    useCreateRecommendationRequestMock.mockReturnValue({ create, loading: false, error: null })

    render(<RecommendationPurpose />)
    await user.click(screen.getByRole("button", { name: "대안 찾기" }))
    await waitFor(() => {
      expect(screen.getByText(/다른 목적을 선택해 주세요/)).toBeInTheDocument()
    })

    await user.click(screen.getByText("역사·문화"))

    expect(screen.queryByText(/다른 목적을 선택해 주세요/)).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "대안 찾기" })).toBeInTheDocument()
  })

  it("검색 중에는 태그를 바꿀 수 없고, 응답이 도착한 뒤에는 다시 바꿀 수 있다", async () => {
    // A로 검색 중에 B로 바꾸면, A의 응답(예: 후보 없음)이 화면엔 B가 선택된 채로 뜬다 —
    // 아직 검색하지도 않은 B가 후보 없는 것처럼 보이는 문제(2026-09-18, 코드 리뷰로 발견).
    // 검색 중 태그 버튼을 막아 이 경로 자체를 없앤다.
    const user = userEvent.setup()
    const pending = deferred<{
      requestId: string
      tripPlaceId: string
      searchMode: string
      status: "success" | "no_candidate"
      candidateCount: number
      excludedCount: number
    }>()
    useCreateRecommendationRequestMock.mockImplementation(() => {
      const [loading, setLoading] = useState(false)
      const create = useCallback(async () => {
        setLoading(true)
        try {
          return await pending.promise
        } finally {
          setLoading(false)
        }
      }, [])
      return { create, loading, error: null }
    })

    render(<RecommendationPurpose />)
    await user.click(screen.getByRole("button", { name: "대안 찾기" }))

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "역사·문화" })).toBeDisabled()
    })
    expect(screen.getByRole("button", { name: "가족 활동" })).toBeDisabled()

    await act(async () => {
      pending.resolve({
        requestId: "req-1",
        tripPlaceId: "tp-1",
        searchMode: "default",
        status: "no_candidate",
        candidateCount: 0,
        excludedCount: 0,
      })
    })

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "역사·문화" })).not.toBeDisabled()
    })
  })
})
