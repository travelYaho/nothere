/**
 * 일정 점검 결과 — STEP4 분석 결과를 전체 장소 목록으로 보여주고,
 * 혼잡한 장소는 카드에서 바로 대안보기/유지를 할 수 있게 한다.
 */
import { useCallback, useEffect, useRef, useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { CongestionCard } from "@/components/common/cards"
import { Button } from "@/components/common/primitives"
import { BasicHeader } from "@/components/layout/navigation"
import {
  fetchAnalysis,
  keepTripPlace,
  toUiCongestion,
  useAccessToken,
  useRunAnalysis,
} from "@/features/recommendation"
import type { AnalysisItem } from "@/features/recommendation"
import { useSession } from "@/store/sessionStore"

type LocationState = {
  analysis?: { items: AnalysisItem[] }
} | null

function isCrowdedPending(item: AnalysisItem) {
  return item.level === "high" && item.resolutionStatus === "pending" && !item.isFixed
}

// analysisStatus는 고정/교체 여부와 무관하게 그 자체로 참이다 — "유지"나 "교체"를
// 선택했다는 사실이 "분석이 성공했다"는 뜻은 아니다(코드 리뷰로 발견, 2026-09-19). 예를
// 들어 예전에 혼잡(high)으로 떠서 "유지"한 장소도, 이후 일정이 바뀌어 재분석이 걸리면
// (trip.needs_reanalysis) 다시 분석되고 이번엔 API 호출이 실패할 수 있다 — 그런데도
// isFixed만 보고 "이미 처리됨"으로 묶어 실패 집계에서 빼면, 사용자는 그 장소가 실제로는
// 한 번도 성공적으로 분석되지 못했다는 걸 알 방법이 없다. 그래서 이 두 함수는
// resolutionStatus/isFixed를 전혀 보지 않고 analysisStatus만으로 판단한다.
function isFailedAnalysis(item: AnalysisItem) {
  return item.analysisStatus === "failed"
}
function isUnavailableAnalysis(item: AnalysisItem) {
  return item.analysisStatus === "unavailable"
}

function needsFreshAnalysis(items: AnalysisItem[]) {
  return items.some((item) => !item.analyzedAt)
}

// 재분석 응답으로 목록 전체를 바꿔 쓰면(setItems(fresh.items)) 그 사이 사용자가 "유지"
// 등으로 로컬에만 반영한 변경(isFixed 등)이 재분석 시작 시점의 낡은 값으로 덮일 수 있다
// (코드 리뷰로 발견, 2026-09-19). 분석 관련 필드만 갱신하고 나머지(isFixed,
// resolutionStatus, replacedFrom 등 사용자 동작으로 바뀌는 필드)는 현재 값을 그대로 둔다.
// tripPlaceId만으로 짝짓지 않고 placeId까지 같을 때만 병합한다 — 다른 탭 등에서 그 사이
// 같은 자리의 장소가 바뀌었다면 tripPlaceId는 그대로라도 placeId가 달라지고, 그 경우
// 응답의 혼잡도가 화면에 남아있는 장소 이름과 맞지 않는 값일 수 있다(코드 리뷰로 발견,
// 2026-09-19). trip_place 구성 자체가 다르면(다른 탭에서 장소가 추가·삭제된 경우) 부분
// 병합 자체가 의미 없으므로 전부 재조회 대상으로 돌린다. 불일치가 있는 항목은 병합하지
// 않고 남겨두며, 호출 쪽이 mismatchedIds를 보고 목록을 다시 조회하도록 한다. 불일치
// 여부는 needsRefetch로 따로 반환한다 — prevItems가 빈 배열이면 mismatchedIds도 항상
// 빈 배열이 되어(map 결과라서) "불일치 없음"으로 잘못 읽힐 수 있었다(코드 리뷰로 발견,
// 2026-09-19 — 기존 target이 0개인데 새 응답에 장소가 있는 경계 사례).
export function mergeAnalysisFields(
  prevItems: AnalysisItem[],
  freshItems: AnalysisItem[],
): { items: AnalysisItem[]; mismatchedIds: string[]; needsRefetch: boolean } {
  const prevIds = new Set(prevItems.map((item) => item.tripPlaceId))
  const freshIds = new Set(freshItems.map((item) => item.tripPlaceId))
  const sameTripPlaces = prevIds.size === freshIds.size && [...prevIds].every((id) => freshIds.has(id))
  if (!sameTripPlaces) {
    return {
      items: prevItems,
      mismatchedIds: prevItems.map((item) => item.tripPlaceId),
      needsRefetch: true,
    }
  }

  const freshByPlace = new Map(freshItems.map((item) => [item.tripPlaceId, item]))
  const mismatchedIds: string[] = []
  const items = prevItems.map((prev) => {
    const fresh = freshByPlace.get(prev.tripPlaceId)
    if (!fresh) return prev
    if (fresh.placeId !== prev.placeId) {
      mismatchedIds.push(prev.tripPlaceId)
      return prev
    }
    return {
      ...prev,
      analysisStatus: fresh.analysisStatus,
      level: fresh.level,
      unknownReason: fresh.unknownReason,
      ruleVersion: fresh.ruleVersion,
      analyzedAt: fresh.analyzedAt,
    }
  })
  return { items, mismatchedIds, needsRefetch: mismatchedIds.length > 0 }
}

// refetchUnresolved는 staleCount와 별개다 — trip_place 구성 자체가 달라 지목할 기존
// 카드가 없는 경우(빈 목록 불일치)에도 재조회가 진행 중이거나 실패한 상태면 참이다(코드
// 리뷰로 발견, 2026-09-19 — staleCount만 보면 이 경우 "확인 완료"로 잘못 보였다). 카드 ID
// 개수만으로 전체 목록이 최신이라고 판단하면 안 된다.
function buildBannerText(
  crowdedCount: number,
  staleCount: number,
  refetchUnresolved: boolean,
  notAnalyzedCount: number,
  analyzingCount: number,
): string {
  if (crowdedCount > 0) return `남은 혼잡 ${crowdedCount}곳`
  if (staleCount > 0) return `최신 일정 확인이 필요한 장소 ${staleCount}곳`
  if (refetchUnresolved) return "일정 목록을 다시 확인해야 해요"
  if (notAnalyzedCount > 0) return `분석하지 못한 장소 ${notAnalyzedCount}곳`
  if (analyzingCount > 0) return `혼잡도 확인 중 ${analyzingCount}곳`
  return "모든 혼잡 장소를 확인했어요"
}

function buildBannerSubText(
  crowdedCount: number,
  staleCount: number,
  refetchUnresolved: boolean,
  hasRefetchError: boolean,
  failedCount: number,
  unavailableCount: number,
  analyzingCount: number,
): string | null {
  if (crowdedCount > 0) {
    const notAnalyzedCount = failedCount + unavailableCount
    const parts = ["계속 점검하거나 지금 확정할 수 있어요"]
    if (staleCount > 0) parts.push(`최신 확인 필요 ${staleCount}곳`)
    if (notAnalyzedCount > 0) parts.push(`분석하지 못한 장소 ${notAnalyzedCount}곳`)
    if (analyzingCount > 0) parts.push(`확인 중 ${analyzingCount}곳`)
    return parts.join(" · ")
  }
  if (staleCount > 0 || refetchUnresolved) {
    // "다시 조회하기" 버튼은 refetchError가 있을 때만 렌더링된다 — 재조회가 아직
    // 진행 중일 때 이 버튼을 안내하면 화면에 없는 버튼을 가리키게 된다(코드 리뷰로
    // 발견, 2026-09-19).
    return hasRefetchError
      ? "아래에서 최신 일정을 다시 조회할 수 있어요"
      : "최신 일정을 확인하고 있어요"
  }
  if (failedCount > 0) return "아래 카드에서 다시 시도할 수 있어요"
  if (unavailableCount > 0) return "일부 장소는 혼잡도 정보를 제공하지 못해요"
  if (analyzingCount > 0) return "잠시만 기다려 주세요"
  return null
}

export default function RemainingCongested() {
  const { tripId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const token = useAccessToken()
  const { isLoading: sessionLoading } = useSession()
  // useRunAnalysis()가 들고 있는 loading/error는 이 훅 인스턴스 하나가 공유하는 단일
  // 상태라, 트립을 넘어가며 재분석이 겹치면 다른 트립(실행)의 완료·실패가 지금 화면의
  // loading/error를 건드릴 수 있다(코드 리뷰로 발견, 2026-09-19). 그래서 이 컴포넌트는
  // run만 가져다 쓰고, 화면에 보여줄 진행 상태(analyzingIds)·오류(reanalysisError)는
  // executionRef로 직접 보호하는 아래 로컬 상태로 따로 관리한다.
  const { run: runAnalysis } = useRunAnalysis(tripId)

  const [items, setItems] = useState<AnalysisItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // 배경에서 재분석 중인 trip_place_id 집합 — 목록은 GET 완료 즉시 보여주고, 이 안에 든
  // 카드만 "혼잡도 확인 중"으로 표시한다(전체 화면을 가리지 않는다).
  const [analyzingIds, setAnalyzingIds] = useState<Set<string>>(new Set())
  const [reanalysisError, setReanalysisError] = useState<string | null>(null)
  // placeId 불일치로 목록을 다시 조회할 때만 쓰는 별도 오류 — 재분석 실패(reanalysisError)
  // 와 원인이 다르고 복구 방법도 다르다(재분석 POST 재시도가 아니라 GET 재시도).
  const [refetchError, setRefetchError] = useState<string | null>(null)
  // "확인 중"(analyzingIds)과는 별개다 — 재조회가 실패하면 진행 중 표시는 꺼야 하지만
  // (무한 로딩 방지), 그렇다고 화면에 남아있는 값이 최신이 되는 건 아니다(코드 리뷰로
  // 발견, 2026-09-19 — 재조회 실패 시 analyzingIds에서만 빼면 낡은 등급·대안보기/유지
  // 버튼이 다시 떠서, 화면엔 교체 전 장소가 보이는데 "유지"를 누르면 tripPlaceId 기준으로
  // 서버는 이미 교체된 장소를 고정할 수 있었다). 재조회가 성공할 때까지는 여기 남아
  // 있는 카드의 등급·행동 버튼을 전부 숨긴다.
  const [staleIds, setStaleIds] = useState<Set<string>>(new Set())
  // staleIds만으로는 "재조회가 필요/진행/실패했지만 구체적으로 지목할 기존 카드가 없는"
  // 경우를 못 잡는다 — trip_place 구성 자체가 다른데 기존 목록이 비어 있으면(다른 탭에서
  // 새로 생긴 경우 등) targetIds가 빈 배열이라 staleIds에 아무것도 안 들어간다(코드 리뷰로
  // 발견, 2026-09-19). 상단 요약이 "모든 확인 완료"로 잘못 보이지 않도록 이 상태를 따로 둔다.
  const [isRefetching, setIsRefetching] = useState(false)
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set())
  const [keepErrors, setKeepErrors] = useState<Record<string, string>>({})
  const firstCrowdedRef = useRef<HTMLDivElement>(null)
  // 이 effect가 두 번 걸리면(StrictMode 개발 중복 마운트, 혹은 의존성 재실행) 예전 코드는
  // 두 실행 다 끝까지 runAnalysis()(트립 전체 재분석 POST)를 그대로 실행했다 — cancelled
  // 플래그는 결과를 화면에 반영할지만 막았을 뿐, 그 비싼 호출 자체를 막지 않았다(실사용
  // 로그에서 같은 지역 집중률 조회가 거의 동시에 두 번 도는 것으로 확인됨, 2026-09-19
  // 코드 리뷰). 실행마다 증가하는 번호로 "지금 이 실행이 여전히 최신인지"를 각 await
  // 지점에서 확인해, 뒤처진 실행이 runAnalysis()를 시작하지 않도록 막는다. 화면을 완전히
  // 벗어나(언마운트) GET 응답이 늦게 와도 같은 방식으로 걸려야 하므로, effect cleanup에서도
  // "아직 아무도 이 번호를 앞지르지 않았으면" 한 번 더 올려 무효화한다(2차 리뷰로 발견 —
  // 처음엔 새 실행이 시작될 때만 번호를 올렸어서 언마운트 후 응답엔 이 가드가 전혀 안 걸렸다).
  const executionRef = useRef(0)
  // executionRef만으로는 "이미 시작된 POST"끼리의 경합은 못 막는다 — 실행 A가 runAnalysis()를
  // await하는 도중에 실행 B가 시작되면, A는 이미 되돌릴 수 없이 요청을 보낸 뒤라 B도 같은
  // 트립에 대해 또 요청을 보낼 수 있다(2차 리뷰로 발견). 트립ID별로 "지금 진행 중인 재분석
  // Promise"를 기억해 두면, 같은 트립에 대한 동시 시도는 그 Promise를 나눠 쓰고, 다른
  // 트립의 재분석은(맵의 키가 다르므로) 전혀 막지 않는다.
  const inFlightAnalysisByTripRef = useRef<Map<string, ReturnType<typeof runAnalysis>>>(new Map())

  // 같은 tripId로 이미 재분석이 진행 중이면 그 Promise를 그대로 나눠 쓴다 — 새 POST를 또
  // 보내지 않는다. 자동 재분석(아래 effect)과 카드의 수동 "다시 시도"(handleRetry)가 동시에
  // 걸려도 이 함수 하나를 같이 쓰므로 중복되지 않는다.
  const startAnalysisIfNeeded = useCallback((): ReturnType<typeof runAnalysis> => {
    if (!tripId) return Promise.resolve(null)
    const inFlight = inFlightAnalysisByTripRef.current
    const existing = inFlight.get(tripId)
    if (existing) return existing
    const promise = runAnalysis().finally(() => {
      if (inFlight.get(tripId) === promise) inFlight.delete(tripId)
    })
    inFlight.set(tripId, promise)
    return promise
  }, [tripId, runAnalysis])

  // placeId/구성 불일치로 목록이 못 미더워졌을 때 다시 GET한다 — 재분석(POST)과는 다른
  // 경로다: 여기서 필요한 건 "화면을 최신 DB 상태와 맞추는 것"이지 "다시 분석을 도는 것"이
  // 아니라서, 실패해도 재분석 POST를 다시 보내지 않고 이 GET만 재시도할 수 있게 한다
  // (코드 리뷰로 발견, 2026-09-19 — 이전엔 이 재조회에 오류 처리가 전혀 없어서 실패하면
  // 처리 안 된 Promise 거부만 남고 화면은 낡은 목록에 멈춰 있었다).
  const refetchList = useCallback(
    (myExecution: number, targetIds: string[]) => {
      if (!tripId) return
      const myTripId = tripId
      setRefetchError(null)
      setIsRefetching(true)
      // "확인 중"과 "최신 상태 미확인(staleIds)"을 둘 다 켠다 — 이 함수는 최초 감지
      // 시점과 "다시 조회하기" 재시도 양쪽에서 불리므로, 재시도할 때도 이 카드들이
      // analyzing(스피너)·stale(행동 제한) 둘 다 다시 걸려야 한다. targetIds가 빈
      // 배열일 수도 있다(trip_place 구성 자체가 달라 지목할 기존 카드가 없는 경우) —
      // 그때를 위해 isRefetching을 별도로 둔다.
      setAnalyzingIds((prev) => new Set([...prev, ...targetIds]))
      setStaleIds((prev) => new Set([...prev, ...targetIds]))
      fetchAnalysis(token, myTripId)
        .then((freshResult) => {
          if (executionRef.current !== myExecution) return
          // 성공한 재조회는 전체 목록의 최신 상태를 반영한다 — staleIds도 전부 해제한다.
          setItems(freshResult.items)
          setAnalyzingIds(new Set())
          setStaleIds(new Set())
          setIsRefetching(false)
        })
        .catch((e) => {
          if (executionRef.current !== myExecution) return
          // 무한 로딩 스피너는 없애지만(analyzingIds에서 뺀다), 실패했다고 화면에 남은 값이
          // 최신이 되는 건 아니다 — staleIds는 그대로 남겨서, 성공적으로 재조회하기 전까지
          // 이 카드들의 등급·행동 버튼을 계속 숨긴다(코드 리뷰로 발견, 2026-09-19 — 이전엔
          // 여기서 analyzingIds만 지워서 낡은 장소의 등급·대안보기·유지가 다시 나타났다.
          // 특히 "유지"는 tripPlaceId로 요청하므로, 화면엔 교체 전 장소가 보이는데 서버는
          // 이미 교체된 장소를 고정 처리할 수 있었다). isRefetching도 false로 끄지만
          // refetchError가 남아 있는 한 상단 요약은 계속 "확인 필요"로 취급한다.
          setAnalyzingIds((prev) => {
            const next = new Set(prev)
            targetIds.forEach((id) => next.delete(id))
            return next
          })
          setIsRefetching(false)
          setRefetchError(e instanceof Error ? e.message : "최신 일정 조회에 실패했어요.")
        })
    },
    [tripId, token],
  )

  // 자동 조회 effect와 수동 "다시 시도"(handleRetry) 둘 다 이 함수 하나로 배경 재분석을
  // 시작·마무리한다 — 로직이 두 곳에 따로 있으면 한쪽만 고치고 다른 쪽을 놓치기 쉽다.
  // currentItems를 인자로 받는다 — 호출 쪽이 그 시점에 알고 있는 목록을 그대로 건넨다.
  // items state를 가리키는 ref를 따로 두고 비동기 콜백에서 읽는 방식은 시도했다가
  // 되돌렸다 — ref를 setState 갱신 함수 안에서 갱신하면 "그 갱신 함수가 호출 즉시 동기
  // 실행된다"는 React 내부 동작에 기대게 되고(공개된 보장이 아님), 대신 useEffect로
  // 커밋 후에 동기화하면 이번엔 반대로 "커밋+effect가 아직 안 돌았는데 그 전에 비동기
  // 콜백이 먼저 ref를 읽는" 경우가 실제로 재현됐다(테스트로 직접 확인, 2026-09-19 — 두
  // 방식 다 신뢰할 수 없었다). 그래서 이제 두 용도를 분리한다: "지금 재분석 대상을
  // 표시"·"불일치 여부 판단"은 이 함수가 받은 currentItems(호출 시점 스냅샷)만 쓰고,
  // "실제로 화면에 반영할 병합"은 setItems의 갱신 함수 형태(React가 최신 상태를 인자로
  // 준다고 보장하는 유일한 방법)만 쓴다 — 둘 다 ref가 필요 없다.
  const runBackgroundAnalysis = useCallback(
    (myExecution: number, currentItems: AnalysisItem[]) => {
      if (!tripId) return
      const myTripId = tripId
      // 어떤 카드가 실제로 다시 분석될지는 API가 알려주지 않는다 — 평소엔 analysis_status가
      // success+level 있는 카드를 건너뛰지만, trip.needs_reanalysis가 켜져 있으면 그 예외로
      // 이미 success인 카드까지 전부 다시 분석된다(코드 리뷰로 발견, 2026-09-19 — "실제로
      // 갱신될 카드만 정확히 표시한다"는 이전 구현은 이 경우를 놓쳐서, 재분석 중인 success
      // 카드가 낡은 등급과 대안보기/유지 버튼을 그대로 보여줄 수 있었다). 어느 카드가
      // 대상인지 미리 알 방법이 없으므로, 오늘 범위에서는 안전하게 전체 카드를 "확인
      // 중"으로 표시한다.
      setAnalyzingIds(new Set(currentItems.map((item) => item.tripPlaceId)))
      setReanalysisError(null)
      setRefetchError(null)

      startAnalysisIfNeeded().then((rerun) => {
        if (executionRef.current !== myExecution) return
        if (rerun && rerun.tripId === myTripId) {
          // 불일치(장소가 그 사이 바뀌었는지) 판단은 재분석 시작 시점 스냅샷(currentItems)
          // 기준으로 충분하다 — placeId는 "유지" 같은 로컬 동작으로 바뀌는 필드가 아니라서,
          // 그 사이 handleKeep이 있었어도 이 판단 자체는 흔들리지 않는다. needsRefetch는
          // mismatchedIds.length와 별개로 반환된다 — currentItems가 빈 배열이면
          // mismatchedIds도 항상 빈 배열이라(map 결과), 그 길이만으로는 "구성 자체가
          // 다르다"는 불일치를 놓칠 수 있었다(코드 리뷰로 발견, 2026-09-19).
          const { mismatchedIds, needsRefetch } = mergeAnalysisFields(currentItems, rerun.items)
          // 실제 화면 반영은 항상 그 시점의 진짜 최신 상태(prev) 기준으로 병합한다 — "유지"
          // 등으로 그 사이 바뀐 필드가 있어도 함수형 갱신이라 놓치지 않는다.
          setItems((prev) => (prev ? mergeAnalysisFields(prev, rerun.items).items : rerun.items))
          if (needsRefetch) {
            // 이 함수 시작부에서 currentItems 전체를 analyzingIds에 넣어뒀는데, refetchList()의
            // analyzingIds 갱신은 더하기만 하고 빼지 않는다 — 여기서 먼저 전부 비우지 않으면
            // 불일치 없이 정상 병합된 카드들이 analyzingIds에 계속 남고, 재조회가 실패하면
            // (catch가 mismatchedIds만 빼므로) 그 카드들은 영영 "확인 중"에 갇힌다(코드
            // 리뷰로 발견, 2026-09-19). 같은 자리의 장소(또는 trip_place 구성) 자체가 그
            // 사이 바뀐 것으로 보이는(다른 탭 등) mismatchedIds만 refetchList()가 다시
            // "확인 중"+"확인 필요"로 표시하고 목록을 다시 조회해서 화면과 실제 상태를 맞춘다.
            setAnalyzingIds(new Set())
            refetchList(myExecution, mismatchedIds)
          } else {
            setAnalyzingIds(new Set())
          }
        } else {
          setAnalyzingIds(new Set())
          if (!rerun) {
            setReanalysisError("일부 장소의 혼잡도 확인에 실패했어요. 다시 분석할 수 있어요.")
          }
        }
      })
    },
    [tripId, startAnalysisIfNeeded, refetchList],
  )

  // location.state는 새로고침에도 남아 있을 수 있다. 재렌더/재실행 때마다 다시 읽으면
  // 그 사이 지워졌는지에 따라 분기가 흔들릴 수 있으므로, 이 마운트에서 처음 읽은 값을
  // 고정해서 쓰고 곧바로(useEffect) 지운다 — 이후 새로고침에서는 다시 쓰이지 않는다.
  const [pendingState] = useState<LocationState>(() => location.state as LocationState)

  useEffect(() => {
    if (pendingState) {
      navigate(location.pathname, { replace: true, state: null })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!tripId) return

    // 로딩 화면(TripAnalysisLoading)이 이미 최신 분석 결과를 들고 넘어온 경우 — 재조회 없음.
    if (pendingState?.analysis) {
      setItems(pendingState.analysis.items)
      setLoading(false)
      setAnalyzingIds(new Set())
      setReanalysisError(null)
      setRefetchError(null)
      setStaleIds(new Set())
      setIsRefetching(false)
      return
    }

    // 세션(토큰) 로딩이 끝나기 전에 호출하면 항상 401로 실패한다 — 기다렸다가 부른다.
    if (sessionLoading) return

    const myExecution = ++executionRef.current
    setLoading(true)
    setError(null)
    setReanalysisError(null)
    // refetchError/staleIds도 여기서 지운다 — 안 지우면 A 트립에서 실패한 재조회 오류가
    // B 트립으로 넘어간 뒤에도 화면에 남는다(코드 리뷰로 발견, 2026-09-19 — reanalysisError
    // 만 지우고 이 둘은 빠져 있었다).
    setRefetchError(null)
    setStaleIds(new Set())
    setIsRefetching(false)

    // 저장된 분석을 먼저 GET해서 목록을 곧바로 보여준다 — 재분석(POST) 완료까지 화면
    // 전체를 "확인 중…"으로 가리지 않는다(코드 리뷰로 발견, 2026-09-19 — 예전엔 이 GET 뒤
    // 재분석까지 끝나야 목록이 나타나서, 교체가 이미 저장됐어도 ~23초를 그냥 기다려야 했다).
    fetchAnalysis(token, tripId)
      .then((result) => {
        if (executionRef.current !== myExecution) return
        setItems(result.items)
        setLoading(false)

        if (!needsFreshAnalysis(result.items)) {
          setAnalyzingIds(new Set())
          return
        }
        runBackgroundAnalysis(myExecution, result.items)
      })
      .catch((e) => {
        if (executionRef.current !== myExecution) return
        setError(e instanceof Error ? e.message : "조회 실패")
        setLoading(false)
      })

    // 언마운트든 의존성 변경으로 인한 재실행이든, cleanup이 불렸다는 건 "이 실행을 더 이상
    // 신뢰하면 안 된다"는 뜻이다. 다만 이미 새 실행이 시작돼 번호를 앞질러 놨다면(의존성
    // 변경으로 인한 재실행 쪽은 React가 cleanup을 먼저 부르므로 보통은 아직 아니다) 그
    // 값을 덮어써서 무효화하면 안 된다 — 그래서 "여전히 내 번호와 같을 때만" 올린다.
    return () => {
      if (executionRef.current === myExecution) {
        executionRef.current += 1
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId, sessionLoading, token])

  const handleKeep = async (item: AnalysisItem) => {
    if (savingIds.has(item.tripPlaceId)) return
    setSavingIds((prev) => new Set(prev).add(item.tripPlaceId))
    setKeepErrors((prev) => {
      if (!(item.tripPlaceId in prev)) return prev
      const next = { ...prev }
      delete next[item.tripPlaceId]
      return next
    })
    try {
      await keepTripPlace(item.tripPlaceId)
      setItems((prev) =>
        prev
          ? prev.map((i) => (i.tripPlaceId === item.tripPlaceId ? { ...i, isFixed: true } : i))
          : prev,
      )
    } catch (e) {
      setKeepErrors((prev) => ({
        ...prev,
        [item.tripPlaceId]: e instanceof Error ? e.message : "저장 실패",
      }))
    } finally {
      setSavingIds((prev) => {
        const next = new Set(prev)
        next.delete(item.tripPlaceId)
        return next
      })
    }
  }

  // executionRef 스냅샷은 자동 조회 effect와 같은 이유로 여기서도 필요하다 — "다시
  // 시도"가 끝나기 전에 다른 트립으로 넘어가거나 화면을 벗어나도, runBackgroundAnalysis
  // 내부의 executionRef 검사가 그 낡은 실행의 결과 반영을 막아준다(코드 리뷰로 발견,
  // 2026-09-19). 카드별 재시도와 배너의 "다시 분석하기" 둘 다 이 함수 하나를 쓴다. items는
  // 클릭 시점 렌더의 값을 그대로 쓴다 — 클릭은 항상 정상적인 렌더-커밋 이후에 일어나므로
  // 이 값이 최신이다.
  const handleRetry = () => {
    runBackgroundAnalysis(executionRef.current, items ?? [])
  }

  // 지금 배경에서 재분석 중이거나(analyzingIds) 재조회 결과를 못 믿는(staleIds) 카드는
  // 어느 집계에도(혼잡·실패·정보부족) 안 들어간다 — 둘 다 "낡은 값을 근거로 판단하면
  // 안 되는" 상태다. 재조회가 실패하면 analyzingIds에서는 빠지지만 staleIds는 남으므로,
  // staleIds를 빼지 않으면 카드는 "최신 정보 확인 필요"인데 상단은 그 낡은 값 그대로
  // "남은 혼잡 N곳"이나 "모든 혼잡 장소를 확인했어요"를 보여주는 모순이 생겼다(코드
  // 리뷰로 발견, 2026-09-19).
  const isPendingOrStale = (id: string) => analyzingIds.has(id) || staleIds.has(id)
  const crowdedCount = (items ?? []).filter(
    (item) => isCrowdedPending(item) && !isPendingOrStale(item.tripPlaceId),
  ).length
  const failedCount = (items ?? []).filter(
    (item) => isFailedAnalysis(item) && !isPendingOrStale(item.tripPlaceId),
  ).length
  const unavailableCount = (items ?? []).filter(
    (item) => isUnavailableAnalysis(item) && !isPendingOrStale(item.tripPlaceId),
  ).length
  const notAnalyzedCount = failedCount + unavailableCount
  const analyzingCount = analyzingIds.size
  const staleCount = staleIds.size
  // 빈 목록 불일치처럼 지목할 기존 카드가 없어도, 재조회가 진행 중이거나 실패해서 아직
  // "전체가 최신"이라고 확신할 수 없는 상태다.
  const refetchUnresolved = staleCount > 0 || isRefetching || refetchError !== null
  const firstCrowdedId = (items ?? []).find(
    (item) => isCrowdedPending(item) && !isPendingOrStale(item.tripPlaceId),
  )?.tripPlaceId

  const goConfirm = () => navigate(`/trips/${tripId}/confirm`)
  const scrollToRemaining = () => {
    firstCrowdedRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })
  }

  const placeList = items
    ? items.map((item) => {
        const showActions = item.resolutionStatus === "pending" && !item.isFixed
        const isFirstCrowded = item.tripPlaceId === firstCrowdedId
        const analysisFailed = item.analysisStatus === "failed"
        const analyzing = analyzingIds.has(item.tripPlaceId)
        const stale = staleIds.has(item.tripPlaceId)
        return (
          <div key={item.tripPlaceId} ref={isFirstCrowded ? firstCrowdedRef : undefined}>
            <CongestionCard
              time={item.visitTime ?? ""}
              place={item.placeName}
              level={toUiCongestion(item.level)}
              showActions={showActions}
              replacedFrom={item.replacedFrom}
              onAlternative={() =>
                navigate(`/trips/${tripId}/places/${item.tripPlaceId}/purpose`)
              }
              onKeep={() => void handleKeep(item)}
              analysisFailed={analysisFailed}
              onRetry={analysisFailed ? () => void handleRetry() : undefined}
              analyzing={analyzing}
              stale={stale}
            />
            {keepErrors[item.tripPlaceId] && (
              <p className="mt-1 text-[12px] text-congestion-high">
                {keepErrors[item.tripPlaceId]}
              </p>
            )}
          </div>
        )
      })
    : null

  return (
    <div className="relative flex min-h-screen flex-1 flex-col">
      <BasicHeader
        title="일정 점검 결과"
        onBack={() => navigate(-1)}
        right={
          <button
            type="button"
            className="text-[13px] font-bold leading-5 text-primary"
            // replace: 장소를 고쳐서 다시 점검하면 이 결과는 낡은 값이 되므로,
            // 뒤로가기가 이 결과 화면으로 다시 돌아오지 않게 히스토리에서 대체한다.
            onClick={() => navigate(`/trips/${tripId}/places`, { replace: true })}
          >
            일정 수정
          </button>
        }
      />

      {loading && <p className="px-5 pt-2 text-[13px] text-ink-muted">확인 중…</p>}
      {error && <p className="px-5 pt-2 text-[13px] text-congestion-high">{error}</p>}

      {!loading && !error && items && (
        <>
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pt-2">
            <div
              className={[
                "rounded-2xl px-4 py-[14px]",
                crowdedCount === 0 && (notAnalyzedCount > 0 || analyzingCount > 0 || refetchUnresolved)
                  ? "bg-surface-chip"
                  : "bg-[#E8F6EE]",
              ].join(" ")}
            >
              <p
                className={[
                  "text-[15px] font-extrabold leading-[22.5px]",
                  crowdedCount === 0 && (notAnalyzedCount > 0 || analyzingCount > 0 || refetchUnresolved)
                    ? "text-ink"
                    : "text-[#1F8A56]",
                ].join(" ")}
              >
                {buildBannerText(crowdedCount, staleCount, refetchUnresolved, notAnalyzedCount, analyzingCount)}
              </p>
              {/* 재시도 버튼은 analysisStatus==="failed" 카드에만 있다. unavailable(지역코드
                  없음, 검수 대기 등)은 영구히 고정된 상태가 아니라 예측 데이터 갱신이나 매핑
                  검수 이후 달라질 수 있지만, 지금 다시 누른다고 바로 해결된다고 보장할 수
                  없어 버튼을 주지 않는다. 안내 문구가 버튼의 실제 존재 여부와 어긋나면 안
                  된다(2026-09-19, 코드 리뷰로 발견). analyzingCount는 "확인 중"이라는 별도
                  상태라 실패/정보부족과 겹치지 않는다. staleCount/refetchUnresolved도 같은
                  이유로 분리한다 — 재조회 실패는 재분석 실패와 원인·복구 방법이 다르다. */}
              {buildBannerSubText(
                crowdedCount,
                staleCount,
                refetchUnresolved,
                refetchError !== null,
                failedCount,
                unavailableCount,
                analyzingCount,
              ) && (
                <p
                  className={[
                    "pt-0.5 text-[12px] font-medium leading-[18px]",
                    crowdedCount > 0 ? "text-[#4A8A6C]" : "text-ink-faint",
                  ].join(" ")}
                >
                  {buildBannerSubText(
                    crowdedCount,
                    staleCount,
                    refetchUnresolved,
                    refetchError !== null,
                    failedCount,
                    unavailableCount,
                    analyzingCount,
                  )}
                </p>
              )}
            </div>
            {/* 재분석 POST 자체가 실패(네트워크 오류 등)하면, 실패 전 상태가 "unavailable"
                같은 경우 카드에는 재시도 버튼이 없다(그 버튼은 analysisStatus==="failed"
                카드에만 있음) — 그러면 사용자가 다시 시도할 방법이 아예 없어진다(코드
                리뷰로 발견, 2026-09-19). 일정 단위 재시도 버튼을 여기 따로 둔다. */}
            {reanalysisError && (
              <div className="flex items-center justify-between gap-2 pt-2">
                <p className="text-[12px] text-congestion-high">{reanalysisError}</p>
                <button
                  type="button"
                  onClick={handleRetry}
                  className="shrink-0 text-[12px] font-bold text-primary"
                >
                  다시 분석하기
                </button>
              </div>
            )}
            {/* placeId 불일치로 목록을 다시 조회하다 실패한 경우 — 재분석(POST)과는 원인이
                달라서 별도 문구·버튼을 쓴다. 이 버튼은 GET만 다시 시도한다(코드 리뷰로 발견,
                2026-09-19). */}
            {refetchError && (
              <div className="flex items-center justify-between gap-2 pt-2">
                <p className="text-[12px] text-congestion-high">{refetchError}</p>
                <button
                  type="button"
                  onClick={() => refetchList(executionRef.current, [...staleIds])}
                  className="shrink-0 text-[12px] font-bold text-primary"
                >
                  다시 조회하기
                </button>
              </div>
            )}

            <div className="flex flex-col gap-2.5 pt-3">{placeList}</div>

            <p className="py-4 text-center text-[11px] leading-[16.5px] text-ink-ghost">
              교체 후 이동시간·집중도는 자동 재계산됩니다.
            </p>
          </div>

          <div className="border-t-[0.667px] border-line-soft bg-white/95 px-4 pb-6 pt-3">
            <div className="flex gap-2.5">
              {crowdedCount > 0 && (
                <Button
                  variant="ghost"
                  onClick={scrollToRemaining}
                  className="h-[54px] min-w-0 flex-1 px-4 text-[15px] font-bold"
                >
                  계속 점검하기
                </Button>
              )}
              <Button
                variant="accent"
                onClick={goConfirm}
                className="h-[54px] min-w-0 flex-1"
              >
                현재 일정으로 확정
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
