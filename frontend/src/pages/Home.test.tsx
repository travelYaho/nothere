import { render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { getHomeSummary } from "@/features/trips/api/tripsApi"
import type { FeaturedGuide, HomeResponse } from "@/features/trips/types"
import Home from "./Home"

vi.mock("@/store/sessionStore", () => ({
  useSession: () => ({
    session: { access_token: "token" },
    user: null,
    isLoading: false,
  }),
}))

vi.mock("@/features/trips/api/tripsApi", () => ({
  getHomeSummary: vi.fn(),
}))

const getHomeSummaryMock = vi.mocked(getHomeSummary)

const featured: FeaturedGuide = {
  token: "tok123",
  title: "2026.09.24 친구 여행",
  regionName: "서울특별시",
  likeCount: 2,
  coverImageUrl: "https://img.example/cover.jpg",
}

function homeResponse(overrides: Partial<HomeResponse> = {}): HomeResponse {
  return {
    user: { id: "u1", nickname: "테스터", profileImageUrl: null },
    draftSchedule: null,
    recentSchedules: [],
    featuredGuide: featured,
    ...overrides,
  }
}

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>,
  )
}

describe("Home featured banner", () => {
  beforeEach(() => {
    getHomeSummaryMock.mockReset()
    getHomeSummaryMock.mockResolvedValue(homeResponse())
  })

  it("TODAY'S RECOMMENDATION 배너에 선정된 일정의 표지 이미지를 보여준다", async () => {
    const { container } = renderHome()
    await waitFor(() => {
      expect(container.querySelector("img")?.getAttribute("src")).toBe(
        "https://img.example/cover.jpg",
      )
    })
    expect(screen.getByText("2026.09.24 친구 여행")).toBeInTheDocument()
  })

  it("표지가 없으면 기본 배너 이미지를 유지한다", async () => {
    getHomeSummaryMock.mockResolvedValue(
      homeResponse({ featuredGuide: { ...featured, coverImageUrl: null } }),
    )
    const { container } = renderHome()
    await waitFor(() => {
      expect(screen.getByText("2026.09.24 친구 여행")).toBeInTheDocument()
    })
    expect(container.querySelector("img")?.getAttribute("src")).toContain("unsplash.com")
  })
})
