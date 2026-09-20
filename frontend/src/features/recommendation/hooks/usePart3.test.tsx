/**
 * useCompareFlow()의 비동기 경쟁 상태 처리 검증.
 *
 * 이 훅은 여러 라운드의 코드 리뷰로 문제가 발견·수정된 이력이 있다 — mock/타입체크로는
 * "실제로 경쟁 상태에서 최신 응답만 반영되는지"를 증명하지 못한다는 지적을 받았다
 * (2026-09-18). 그래서 이 테스트는 promise 완료 순서를 직접 통제해서, 늦게 도착한
 * 응답이 최신 상태를 덮어쓰지 않는지를 실제 React 렌더링 사이클로 확인한다.
 */
import { act, renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useCompareFlow } from "./usePart3"
import { ApiError } from "@/types/api"
import type { CompareCandidatesResponse } from "../types/part3"

vi.mock("@/store/sessionStore", () => ({
  useSession: () => ({
    session: { access_token: "test-token" },
    user: null,
    isLoading: false,
  }),
}))

vi.mock("../api/part3Api", () => ({
  scoreRoutes: vi.fn(),
  fetchScoredCandidates: vi.fn(),
  applyReplacement: vi.fn(),
  confirmTrip: vi.fn(),
  createShareLink: vi.fn(),
  fetchPublicGuide: vi.fn(),
  fetchRemainingCongested: vi.fn(),
  fetchReplacementPreview: vi.fn(),
  fetchTripGuide: vi.fn(),
  saveGuideMemo: vi.fn(),
}))

import { fetchScoredCandidates, scoreRoutes } from "../api/part3Api"

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function makeResponse(
  requestId: string,
  tripPlaceId: string,
  candidateId: string,
): CompareCandidatesResponse {
  return {
    originalPlace: { placeId: "orig", name: "원래 장소", congestionLevel: "low" },
    candidates: [
      {
        candidateId,
        placeName: `후보-${candidateId}`,
        experienceScore: 0.8,
        routeScore: 0.7,
        congestionLevel: "low",
        congestionImprovement: "low_to_low",
        extraMinutes: 5,
        distancePrevM: 100,
        distanceNextM: 100,
        reasonText: null,
        isEligible: true,
        exclusionReason: null,
      },
    ],
    requestId,
    tripPlaceId,
  }
}

const scoreRoutesMock = scoreRoutes as unknown as ReturnType<typeof vi.fn>
const fetchScoredMock = fetchScoredCandidates as unknown as ReturnType<typeof vi.fn>

beforeEach(() => {
  scoreRoutesMock.mockReset()
  fetchScoredMock.mockReset()
})

describe("useCompareFlow", () => {
  it("같은 requestId를 두 번 불러도, 늦게 도착한 첫 응답이 두 번째 결과를 덮어쓰지 않는다", async () => {
    const first = deferred<CompareCandidatesResponse>()
    const second = deferred<CompareCandidatesResponse>()
    scoreRoutesMock.mockResolvedValueOnce(undefined)
    scoreRoutesMock.mockResolvedValueOnce(undefined)
    fetchScoredMock.mockImplementationOnce(() => first.promise)
    fetchScoredMock.mockImplementationOnce(() => second.promise)

    const { result } = renderHook(() => useCompareFlow("req-1"))

    let p1!: Promise<void>
    let p2!: Promise<void>
    act(() => {
      p1 = result.current.load()
    })
    act(() => {
      p2 = result.current.load()
    })

    // 두 번째(최신) 호출이 먼저 도착한다.
    await act(async () => {
      second.resolve(makeResponse("req-1", "tp-1", "second-candidate"))
      await p2
    })
    expect(result.current.data?.candidates[0].candidateId).toBe("second-candidate")

    // 그다음 첫 번째(오래된) 호출이 늦게 도착해도 무시돼야 한다.
    await act(async () => {
      first.resolve(makeResponse("req-1", "tp-1", "first-candidate"))
      await p1
    })
    expect(result.current.data?.candidates[0].candidateId).toBe("second-candidate")
  })

  it("A→B→A로 전환한 뒤 가장 오래된 A 응답이 마지막에 도착해도 최신 A 결과를 덮어쓰지 않는다", async () => {
    const staleA = deferred<CompareCandidatesResponse>()
    const b = deferred<CompareCandidatesResponse>()
    const freshA = deferred<CompareCandidatesResponse>()
    scoreRoutesMock.mockResolvedValue(undefined)
    fetchScoredMock.mockImplementationOnce(() => staleA.promise)
    fetchScoredMock.mockImplementationOnce(() => b.promise)
    fetchScoredMock.mockImplementationOnce(() => freshA.promise)

    const { result, rerender } = renderHook(
      ({ requestId }) => useCompareFlow(requestId),
      { initialProps: { requestId: "A" } },
    )

    let pA1!: Promise<void>
    act(() => {
      pA1 = result.current.load() // 오래된 A 호출 — 아직 응답 안 옴
    })

    rerender({ requestId: "B" })
    let pB!: Promise<void>
    act(() => {
      pB = result.current.load()
    })

    rerender({ requestId: "A" })
    let pA2!: Promise<void>
    act(() => {
      pA2 = result.current.load() // 최신 A 호출
    })

    // B 응답 도착
    await act(async () => {
      b.resolve(makeResponse("B", "tp-1", "b-candidate"))
      await pB
    })
    // 최신 A 응답 도착
    await act(async () => {
      freshA.resolve(makeResponse("A", "tp-1", "fresh-a-candidate"))
      await pA2
    })
    expect(result.current.data?.candidates[0].candidateId).toBe("fresh-a-candidate")

    // 가장 오래된 A 호출의 응답이 이제서야 도착 — 무시돼야 한다.
    await act(async () => {
      staleA.resolve(makeResponse("A", "tp-1", "stale-a-candidate"))
      await pA1
    })
    expect(result.current.data?.candidates[0].candidateId).toBe("fresh-a-candidate")
  })

  it("requestId가 없어지면 이전 후보·오류·후보없음 상태를 즉시(비동기 없이) 지운다", async () => {
    scoreRoutesMock.mockResolvedValue(undefined)
    fetchScoredMock.mockResolvedValue(makeResponse("req-1", "tp-1", "cand-1"))

    const { result, rerender } = renderHook(
      ({ requestId }) => useCompareFlow(requestId),
      { initialProps: { requestId: "req-1" as string | undefined } },
    )

    await act(async () => {
      await result.current.load()
    })
    expect(result.current.data?.candidates[0].candidateId).toBe("cand-1")

    rerender({ requestId: undefined })
    act(() => {
      void result.current.load()
    })

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
    expect(result.current.noCandidate).toBe(false)
    expect(result.current.loading).toBe(false)
  })

  it("NO_CANDIDATE ApiError는 noCandidate만 켜고 error는 건드리지 않는다", async () => {
    scoreRoutesMock.mockRejectedValueOnce(
      new ApiError(400, { code: "NO_CANDIDATE", message: "이 조건에 맞는 대안 후보를 찾지 못했습니다." }),
    )

    const { result } = renderHook(() => useCompareFlow("req-1"))
    await act(async () => {
      await result.current.load()
    })

    expect(result.current.noCandidate).toBe(true)
    expect(result.current.error).toBeNull()
    expect(result.current.data).toBeNull()
  })

  it("일반 오류(인증·서버 오류 등)는 error만 채우고 noCandidate는 그대로 둔다", async () => {
    scoreRoutesMock.mockRejectedValueOnce(
      new ApiError(401, { code: "AUTH_TOKEN_EXPIRED", message: "로그인이 만료되었습니다." }),
    )

    const { result } = renderHook(() => useCompareFlow("req-1"))
    await act(async () => {
      await result.current.load()
    })

    expect(result.current.error).toBe("로그인이 만료되었습니다.")
    expect(result.current.noCandidate).toBe(false)
    expect(result.current.data).toBeNull()
  })

  it("최신 조회가 성공한 뒤, 이전 요청의 실패가 늦게 와도 성공 상태를 덮어쓰지 않는다", async () => {
    const staleFailure = deferred<never>()
    scoreRoutesMock.mockImplementationOnce(() => staleFailure.promise as unknown as Promise<void>)
    scoreRoutesMock.mockResolvedValueOnce(undefined)
    fetchScoredMock.mockResolvedValueOnce(makeResponse("req-1", "tp-1", "fresh-candidate"))

    const { result } = renderHook(() => useCompareFlow("req-1"))

    let pStale!: Promise<void>
    act(() => {
      pStale = result.current.load() // scoreRoutes에서 멈춰 있음(아직 실패 안 함)
    })
    await act(async () => {
      await result.current.load() // 두 번째 호출은 바로 성공
    })
    expect(result.current.data?.candidates[0].candidateId).toBe("fresh-candidate")
    expect(result.current.error).toBeNull()

    // 이제서야 첫 번째(오래된) 호출이 실패로 도착 — 최신 성공 상태를 덮으면 안 된다.
    await act(async () => {
      staleFailure.reject(new ApiError(500, { code: "DB_ERROR", message: "서버 오류" }))
      await pStale
    })
    expect(result.current.data?.candidates[0].candidateId).toBe("fresh-candidate")
    expect(result.current.error).toBeNull()
    expect(result.current.noCandidate).toBe(false)
  })

  it("언마운트 후 도착한 응답을 처리해도 예외 없이 끝난다(약한 검증 — 아래 설명 참고)", async () => {
    // 주의: 이 테스트는 "unmount 시 executionRef를 무효화하는 코드가 실제로 setState 호출을
    // 막았는지"를 증명하지 못한다 — React 19 + RTL에서는 언마운트된 함수 컴포넌트의 useState
    // setter를 나중에 불러도 경고/에러가 전혀 나지 않는다는 걸 직접 확인했다(unmount 정리
    // 코드를 일시적으로 지우고 이 테스트를 다시 돌려도 여전히 통과함 — 즉 이 신호는 가드
    // 유무와 무관하게 항상 "조용함"이라 구분력이 없다, 2026-09-18 코드 리뷰로 발견). 그래서
    // "console.error가 없다 → 갱신을 안 했다"는 주장은 하지 않는다 — 이 테스트가 실제로
    // 보장하는 건 "언마운트 후 응답이 와도 테스트 자체가 죽지 않는다"는 것뿐이다. unmount
    // 시 무효화 코드는 그 자체로 흔한 방어적 관례(이 코드베이스의 mountedRef 패턴과 동일한
    // 취지)라 남겨두지만, 이 테스트만으로 "언마운트 보호가 검증됐다"고 설명하지 않는다.
    const slow = deferred<CompareCandidatesResponse>()
    scoreRoutesMock.mockResolvedValue(undefined)
    fetchScoredMock.mockImplementationOnce(() => slow.promise)

    const { result, unmount } = renderHook(() => useCompareFlow("req-1"))

    let p!: Promise<void>
    act(() => {
      p = result.current.load()
    })

    unmount()

    await expect(
      act(async () => {
        slow.resolve(makeResponse("req-1", "tp-1", "late-candidate"))
        await p
      }),
    ).resolves.not.toThrow()
  })

  it("서로 다른 requestId 사이에서는 나중 요청이 이전 요청의 응답을 덮어쓰지 않는다(기존 동작 유지)", async () => {
    const oldReq = deferred<CompareCandidatesResponse>()
    const newReq = deferred<CompareCandidatesResponse>()
    scoreRoutesMock.mockResolvedValue(undefined)
    fetchScoredMock.mockImplementationOnce(() => oldReq.promise)
    fetchScoredMock.mockImplementationOnce(() => newReq.promise)

    const { result, rerender } = renderHook(
      ({ requestId }) => useCompareFlow(requestId),
      { initialProps: { requestId: "old-req" } },
    )

    let pOld!: Promise<void>
    act(() => {
      pOld = result.current.load()
    })

    rerender({ requestId: "new-req" })
    let pNew!: Promise<void>
    act(() => {
      pNew = result.current.load()
    })

    await act(async () => {
      newReq.resolve(makeResponse("new-req", "tp-1", "new-candidate"))
      await pNew
    })
    await act(async () => {
      oldReq.resolve(makeResponse("old-req", "tp-1", "old-candidate"))
      await pOld
    })

    await waitFor(() => {
      expect(result.current.data?.candidates[0].candidateId).toBe("new-candidate")
    })
  })
})
