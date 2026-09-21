import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useTripRegionName } from "./useTripRegionName"

vi.mock("@/features/trips", () => ({ getTripDetail: vi.fn() }))

import { getTripDetail } from "@/features/trips"

const getTripDetailMock = vi.mocked(getTripDetail)

beforeEach(() => {
  getTripDetailMock.mockReset()
})

describe("useTripRegionName", () => {
  it("조회에 성공하면 지역명을 돌려준다", async () => {
    getTripDetailMock.mockResolvedValue({ regionName: "부산광역시" } as never)

    const { result } = renderHook(() => useTripRegionName("trip-1", true))

    await waitFor(() => expect(result.current).toBe("부산광역시"))
    expect(getTripDetailMock).toHaveBeenCalledWith("trip-1")
  })

  it("조회에 실패하면 null이고 오류가 화면으로 번지지 않는다", async () => {
    getTripDetailMock.mockRejectedValue(new Error("401"))

    const { result } = renderHook(() => useTripRegionName("trip-1", true))

    await waitFor(() => expect(getTripDetailMock).toHaveBeenCalled())
    expect(result.current).toBeNull()
  })

  it("세션이 준비되기 전(enabled=false)에는 조회하지 않고, 준비되면 조회한다", async () => {
    getTripDetailMock.mockResolvedValue({ regionName: "서울특별시" } as never)

    const { result, rerender } = renderHook(({ enabled }) => useTripRegionName("trip-1", enabled), {
      initialProps: { enabled: false },
    })
    expect(getTripDetailMock).not.toHaveBeenCalled()

    rerender({ enabled: true })

    await waitFor(() => expect(result.current).toBe("서울특별시"))
  })

  it("tripId가 없으면 조회하지 않는다", () => {
    renderHook(() => useTripRegionName(undefined, true))

    expect(getTripDetailMock).not.toHaveBeenCalled()
  })

  it("일정이 바뀌면 이전 일정의 지역명을 돌려주지 않고, 새 일정 조회가 실패해도 남지 않는다", async () => {
    getTripDetailMock.mockResolvedValueOnce({ regionName: "서울특별시" } as never)
    const { result, rerender } = renderHook(({ id }) => useTripRegionName(id, true), {
      initialProps: { id: "trip-1" },
    })
    await waitFor(() => expect(result.current).toBe("서울특별시"))

    getTripDetailMock.mockRejectedValueOnce(new Error("500"))
    rerender({ id: "trip-2" })

    expect(result.current).toBeNull()
    await waitFor(() => expect(getTripDetailMock).toHaveBeenCalledWith("trip-2"))
    expect(result.current).toBeNull()
  })

  it("이전 일정의 응답이 새 일정 응답보다 늦게 와도 덮어쓰지 않는다", async () => {
    let resolveFirst: (value: unknown) => void = () => {}
    getTripDetailMock.mockReturnValueOnce(new Promise((r) => (resolveFirst = r)) as never)
    getTripDetailMock.mockResolvedValueOnce({ regionName: "부산광역시" } as never)
    const { result, rerender } = renderHook(({ id }) => useTripRegionName(id, true), {
      initialProps: { id: "trip-1" },
    })

    rerender({ id: "trip-2" })
    await waitFor(() => expect(result.current).toBe("부산광역시"))
    resolveFirst({ regionName: "서울특별시" })
    await new Promise((r) => setTimeout(r, 10))

    expect(result.current).toBe("부산광역시")
  })

  // 이 React 버전은 언마운트 뒤의 setState를 아무 신호 없이 무시해서, 취소 처리(cancelled)를 지워도 이
  // 테스트는 통과한다 — 취소 처리가 검증됐다고 주장하지 않고, 예외 없이 끝나는지만 확인한다.
  it("언마운트 뒤에 응답이 늦게 도착해도 예외 없이 끝난다", async () => {
    let resolve: (value: unknown) => void = () => {}
    getTripDetailMock.mockReturnValue(new Promise((r) => (resolve = r)) as never)

    const { result, unmount } = renderHook(() => useTripRegionName("trip-1", true))
    unmount()
    resolve({ regionName: "서울특별시" })
    await Promise.resolve()

    expect(result.current).toBeNull() // 언마운트 시점의 값 그대로
  })
})
