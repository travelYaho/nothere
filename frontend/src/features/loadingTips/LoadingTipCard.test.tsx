import { act, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { LoadingTipCard } from "./LoadingTipCard"
import { COMMON_TIPS, tipsForRegion } from "./tips"

const KIND_LABELS = ["심심풀이 퀴즈", "여행 팁", "알고 계셨나요?"]

function shownText(): string {
  // 카드 안에서 종류 라벨 다음에 오는 문구 본문을 읽는다.
  const label = KIND_LABELS.map((l) => screen.queryByText(l)).find(Boolean)
  return label?.nextElementSibling?.textContent ?? ""
}

beforeEach(() => {
  vi.useFakeTimers()
})
afterEach(() => {
  vi.useRealTimers()
})

describe("LoadingTipCard", () => {
  it("문구 한 개와 종류 라벨을 보여준다", () => {
    render(<LoadingTipCard />)

    expect(KIND_LABELS.some((l) => screen.queryByText(l))).toBe(true)
    expect(shownText().length).toBeGreaterThan(0)
  })

  it("간격이 지나면 다른 문구로 바뀌고 연달아 같은 문구가 나오지 않는다", () => {
    render(<LoadingTipCard intervalMs={1000} />)

    const seen: string[] = [shownText()]
    for (let i = 0; i < 12; i++) {
      act(() => {
        vi.advanceTimersByTime(1000)
      })
      seen.push(shownText())
    }

    for (let i = 1; i < seen.length; i++) expect(seen[i]).not.toBe(seen[i - 1])
    expect(new Set(seen).size).toBeGreaterThan(1)
  })

  it("한 바퀴를 다 돌기 전에는 같은 문구를 반복하지 않는다", () => {
    render(<LoadingTipCard intervalMs={1000} />)

    const seen = [shownText()]
    for (let i = 0; i < COMMON_TIPS.length - 1; i++) {
      act(() => {
        vi.advanceTimersByTime(1000)
      })
      seen.push(shownText())
    }

    expect(new Set(seen).size).toBe(COMMON_TIPS.length)
  })

  it("지역이 뒤늦게 정해져도 지금 보이는 문구는 바뀌지 않고, 이후 순서부터 지역 문구가 섞인다", () => {
    const { rerender } = render(<LoadingTipCard regionName={null} intervalMs={1000} />)
    const before = shownText()

    rerender(<LoadingTipCard regionName="서울특별시" intervalMs={1000} />)
    expect(shownText()).toBe(before)

    const regionTexts = new Set(tipsForRegion("서울특별시").map((t) => t.text))
    let sawRegionTip = false
    for (let i = 0; i < 20 && !sawRegionTip; i++) {
      act(() => {
        vi.advanceTimersByTime(1000)
      })
      sawRegionTip = regionTexts.has(shownText())
    }
    expect(sawRegionTip).toBe(true)
  })

  it("처음부터 지역을 알고 있으면 첫 한 바퀴 안에 지역 문구가 모두, 반복 없이 나온다", () => {
    // 재시도로 카드가 다시 마운트될 때처럼 첫 렌더부터 지역이 정해져 있는 경우.
    const region = tipsForRegion("부산광역시")
    const poolSize = region.length + COMMON_TIPS.length
    render(<LoadingTipCard regionName="부산광역시" intervalMs={1000} />)

    const seen = [shownText()]
    for (let i = 0; i < poolSize - 1; i++) {
      act(() => {
        vi.advanceTimersByTime(1000)
      })
      seen.push(shownText())
    }

    expect(new Set(seen).size).toBe(poolSize)
    for (const tip of region) expect(seen).toContain(tip.text)
  })

  it("지역 문구가 없는 지역에서는 공통 문구만 나온다", () => {
    render(<LoadingTipCard regionName="제주특별자치도" intervalMs={1000} />)

    const common = new Set(COMMON_TIPS.map((t) => t.text))
    for (let i = 0; i < 10; i++) {
      expect(common.has(shownText())).toBe(true)
      act(() => {
        vi.advanceTimersByTime(1000)
      })
    }
  })

  it("오래 걸리면 지연 안내가 나오고, 그 전에는 나오지 않는다", () => {
    render(<LoadingTipCard slowAfterMs={5000} intervalMs={60000} />)

    expect(screen.queryByText(/조회에 시간이 걸리고 있어요/)).toBeNull()
    act(() => {
      vi.advanceTimersByTime(5000)
    })
    expect(screen.getByText(/조회에 시간이 걸리고 있어요/)).toBeInTheDocument()
  })

  it("언마운트하면 남는 타이머가 없다", () => {
    const { unmount } = render(<LoadingTipCard />)

    unmount()

    expect(vi.getTimerCount()).toBe(0)
  })
})

describe("퀴즈", () => {
  // 퀴즈만 골라서 확인하려고 random을 고정하지 않고, 퀴즈가 나올 때까지 넘긴다.
  function advanceUntilQuiz() {
    for (let i = 0; i < 60; i++) {
      if (screen.queryByText("정답 보기")) return true
      act(() => {
        vi.advanceTimersByTime(1000)
      })
    }
    return false
  }

  it("정답은 '정답 보기'를 눌러야 보인다", () => {
    render(<LoadingTipCard regionName="서울특별시" intervalMs={1000} revealHoldMs={5000} />)
    expect(advanceUntilQuiz()).toBe(true)
    const answers = tipsForRegion("서울특별시").filter((t) => t.answer).map((t) => t.answer as string)

    expect(answers.some((a) => screen.queryByText(a))).toBe(false)
    fireEvent.click(screen.getByText("정답 보기"))

    expect(answers.some((a) => screen.queryByText(a))).toBe(true)
    expect(screen.queryByText("정답 보기")).toBeNull()
  })

  it("정답을 본 직후에는 바로 넘어가지 않고 정해진 시간 동안 유지한다", () => {
    render(<LoadingTipCard regionName="서울특별시" intervalMs={1000} revealHoldMs={5000} />)
    expect(advanceUntilQuiz()).toBe(true)
    const question = shownText()

    fireEvent.click(screen.getByText("정답 보기"))
    act(() => {
      vi.advanceTimersByTime(4000)
    })
    expect(shownText()).toBe(question)

    act(() => {
      vi.advanceTimersByTime(1500)
    })
    expect(shownText()).not.toBe(question)
  })
})
