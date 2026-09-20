import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
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

const getCurrentPosition = vi.fn()

describe("Home featured banner", () => {
  beforeEach(() => {
    getHomeSummaryMock.mockReset()
    getHomeSummaryMock.mockResolvedValue(homeResponse())
    getCurrentPosition.mockReset()
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: { getCurrentPosition },
    })
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

  it("위치 아이콘을 누르면 브라우저 위치 권한을 요청한다", async () => {
    const user = userEvent.setup()
    renderHome()
    await user.click(screen.getByRole("button", { name: "위치 권한 설정" }))
    expect(getCurrentPosition).toHaveBeenCalledTimes(1)
  })

  it("위치 권한이 거부되면 설정 안내 팝업을 보여준다", async () => {
    getCurrentPosition.mockImplementation((_ok, err) => {
      err({ code: 1, PERMISSION_DENIED: 1, message: "denied" })
    })
    const user = userEvent.setup()
    renderHome()
    await user.click(screen.getByRole("button", { name: "위치 권한 설정" }))
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument()
    expect(screen.getByText("위치 권한을 허용해 주세요")).toBeInTheDocument()
    expect(screen.getByText(/설정 앱의 앱 권한 메뉴/)).toBeInTheDocument()
  })
})
