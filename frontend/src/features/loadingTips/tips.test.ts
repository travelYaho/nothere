import { describe, expect, it } from "vitest"
import { COMMON_TIPS, shuffledQueue, tipsForRegion } from "./tips"

describe("tipsForRegion", () => {
  it("서울·부산 일정은 각 지역 문구를 돌려준다", () => {
    const seoul = tipsForRegion("서울특별시")
    const busan = tipsForRegion("부산광역시")

    expect(seoul.length).toBeGreaterThan(0)
    expect(busan.length).toBeGreaterThan(0)
    expect(seoul).not.toEqual(busan)
    expect(seoul.some((tip) => tip.text.includes("신발"))).toBe(true)
    expect(busan.some((tip) => tip.text.includes("부산"))).toBe(true)
  })

  it("지원하지 않는 지역이나 값이 없으면 지역 문구 없이 빈 목록이다", () => {
    expect(tipsForRegion("제주특별자치도")).toEqual([])
    expect(tipsForRegion(null)).toEqual([])
    expect(tipsForRegion(undefined)).toEqual([])
    expect(tipsForRegion("")).toEqual([])
  })
})

describe("문구 데이터", () => {
  const all = [...COMMON_TIPS, ...tipsForRegion("서울특별시"), ...tipsForRegion("부산광역시")]

  it("퀴즈에는 정답이 있고 다른 종류에는 정답이 없다", () => {
    for (const tip of all) {
      if (tip.kind === "quiz") expect(tip.answer, tip.text).toBeTruthy()
      else expect(tip.answer, tip.text).toBeUndefined()
    }
  })

  it("문구가 서로 겹치지 않는다(한 바퀴에 같은 문구가 두 번 나오지 않게)", () => {
    const texts = all.map((tip) => tip.text)

    expect(new Set(texts).size).toBe(texts.length)
  })

  it("진행률을 흉내 내거나 혼잡·한적함을 단정하는 표현이 없다", () => {
    const forbidden = ["% 완료", "곧 끝", "거의 다", "한적한 곳을 찾았", "추천드려요"]
    for (const tip of all) {
      for (const word of forbidden) {
        expect(`${tip.text} ${tip.answer ?? ""}`, tip.text).not.toContain(word)
      }
    }
  })
})

describe("shuffledQueue", () => {
  it("풀의 모든 문구를 한 번씩 담는다", () => {
    const queue = shuffledQueue(COMMON_TIPS, null)

    expect(queue).toHaveLength(COMMON_TIPS.length)
    expect(new Set(queue)).toEqual(new Set(COMMON_TIPS))
  })

  it("직전에 보여준 문구가 새 순서의 맨 앞에 오지 않는다", () => {
    const previous = COMMON_TIPS[0]

    // random이 항상 0이면 셔플 결과가 고정돼 맨 앞이 previous가 되는 경우를 만든다.
    const queue = shuffledQueue(COMMON_TIPS, previous, () => 0.999999)
    const first = shuffledQueue(COMMON_TIPS, null, () => 0.999999)[0]
    const forced = shuffledQueue(COMMON_TIPS, first, () => 0.999999)

    expect(queue).toHaveLength(COMMON_TIPS.length)
    expect(forced[0]).not.toBe(first)
  })
})
