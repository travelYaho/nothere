import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import { FlowLoadingView } from "./FlowLoadingView"

vi.mock("@/features/loadingTips/LoadingTipCard", () => ({
  LoadingTipCard: ({ regionName }: { regionName?: string | null }) => (
    <div data-testid="tip-card">{regionName ?? "지역 없음"}</div>
  ),
}))

const STEPS = [
  { label: "확인 중...", progress: 35 },
  { label: "정리 중...", progress: 92 },
] as const

function renderView(props: Partial<React.ComponentProps<typeof FlowLoadingView>> = {}) {
  return render(
    <MemoryRouter>
      <FlowLoadingView
        headerTitle="테스트"
        headerProgress={0.5}
        title="찾고 있어요"
        steps={STEPS}
        stepIndex={0}
        loading
        {...props}
      />
    </MemoryRouter>,
  )
}

describe("FlowLoadingView 대기 문구", () => {
  it("대기 중에는 문구 카드를 보여주고 지역명을 넘긴다", () => {
    renderView({ tipRegionName: "부산광역시" })

    expect(screen.getByTestId("tip-card")).toHaveTextContent("부산광역시")
  })

  it("지역을 몰라도 문구 카드는 보인다", () => {
    renderView()

    expect(screen.getByTestId("tip-card")).toHaveTextContent("지역 없음")
  })

  it("실패로 대기가 끝나면 문구 대신 기존 오류 안내와 다시 시도만 보인다", () => {
    renderView({ loading: false, error: "실패했어요", onRetry: () => {} })

    expect(screen.queryByTestId("tip-card")).toBeNull()
    expect(screen.getByRole("alert")).toHaveTextContent("실패했어요")
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeInTheDocument()
  })

  it("후보 없음 같은 안내 상태에서도 문구가 사라지고 안내가 보인다", () => {
    renderView({ loading: false, notice: "찾지 못했어요", onNoticeAction: () => {} })

    expect(screen.queryByTestId("tip-card")).toBeNull()
    expect(screen.getByText("찾지 못했어요")).toBeInTheDocument()
  })

  it("잘못된 접근(id 없음)이면 문구 없이 오류만 보인다", () => {
    renderView({ missingIdMessage: "일정을 찾을 수 없습니다." })

    expect(screen.queryByTestId("tip-card")).toBeNull()
    expect(screen.getByText("일정을 찾을 수 없습니다.")).toBeInTheDocument()
  })

  it("문구를 추가해도 기존 단계 문구·진행 표시는 그대로다", () => {
    renderView()

    expect(screen.getByRole("status")).toHaveTextContent("확인 중...")
    expect(screen.getAllByRole("progressbar").map((bar) => bar.getAttribute("aria-valuenow"))).toContain("35")
    expect(screen.getByText("1 / 2")).toBeInTheDocument()
  })
})
