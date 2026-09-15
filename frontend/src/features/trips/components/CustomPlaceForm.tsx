/**
 * CustomPlaceForm — "장소 직접 추가" 화면.
 * Figma: 여기말GO / node 48:3842 (프레임 자체 이름은 "여행 조건 온보딩"으로
 * 잘못 붙어 있지만 실제 내용은 장소 직접 추가 폼이다 — 사용자 확인받음)
 */
import { useEffect, useRef, useState, type FormEvent } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Button } from "@/components/common/primitives"
import { FieldLabel, TextInput } from "@/components/common/inputs"
import { Close, Search } from "@/components/common/icons"
import { StepHeader } from "@/features/trips/components/StepHeader"
import { getTripDetail } from "@/features/trips/api/tripsApi"
import { addCustomPlaceToTrip } from "@/features/trips/api/placesApi"
import { ApiError } from "@/types/api"

/** 다음(카카오) 우편번호 서비스 — 실제 존재하는 도로명주소만 선택 가능하게 강제한다. */
const DAUM_POSTCODE_SCRIPT_SRC = "https://t1.daumcdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js"

/**
 * 여행 지역 밖 주소를 걸러내기 위한 시/도 접두어 매핑.
 * 다음 우편번호 검색 결과 주소는 regions 테이블의 정식 명칭("서울특별시")이
 * 아니라 "서울"처럼 축약된 형태로 내려오므로 그 축약형으로 매칭한다
 * (백엔드 PlaceService._REGION_ADDRESS_PREFIXES 와 동일한 기준).
 */
const REGION_ADDRESS_PREFIXES: Record<string, string[]> = {
  서울특별시: ["서울"],
  부산광역시: ["부산"],
}

function isAddressInRegion(address: string, regionName: string | null): boolean {
  const prefixes = regionName ? REGION_ADDRESS_PREFIXES[regionName] : undefined
  if (!prefixes) return true
  return prefixes.some((prefix) => address.startsWith(prefix))
}

interface DaumPostcodeData {
  roadAddress: string
  jibunAddress: string
  autoRoadAddress: string
  autoJibunAddress: string
}

declare global {
  interface Window {
    daum?: {
      Postcode: new (options: {
        oncomplete: (data: DaumPostcodeData) => void
        width?: string | number
        height?: string | number
      }) => { embed: (el: HTMLElement) => void }
    }
  }
}

let daumPostcodeLoadPromise: Promise<void> | null = null

function loadDaumPostcodeScript(): Promise<void> {
  if (window.daum?.Postcode) return Promise.resolve()
  if (daumPostcodeLoadPromise) return daumPostcodeLoadPromise

  daumPostcodeLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script")
    script.src = DAUM_POSTCODE_SCRIPT_SRC
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      daumPostcodeLoadPromise = null
      reject(new Error("주소 검색 스크립트를 불러오지 못했습니다."))
    }
    document.head.appendChild(script)
  })
  return daumPostcodeLoadPromise
}

function pickRoadAddress(data: DaumPostcodeData): string {
  return data.roadAddress || data.autoRoadAddress || data.jibunAddress || data.autoJibunAddress
}

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) {
    if (/failed to fetch|network/i.test(err.message)) {
      return "서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요."
    }
    return err.message
  }
  return "요청 중 문제가 발생했습니다."
}

export function CustomPlaceForm() {
  const { tripId } = useParams<{ tripId: string }>()
  const navigate = useNavigate()

  const [name, setName] = useState("")
  const [baseAddress, setBaseAddress] = useState("")
  const [detailAddress, setDetailAddress] = useState("")
  const [visitTime, setVisitTime] = useState("")
  const [regionName, setRegionName] = useState<string | null>(null)

  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [searchingAddress, setSearchingAddress] = useState(false)
  const [addressSearchOpen, setAddressSearchOpen] = useState(false)
  const addressSearchRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!tripId) return
    getTripDetail(tripId)
      .then((detail) => setRegionName(detail.regionName))
      .catch(() => setRegionName(null))
  }, [tripId])

  async function handleSearchAddress() {
    setError(null)
    setSearchingAddress(true)
    try {
      await loadDaumPostcodeScript()
      setAddressSearchOpen(true)
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setSearchingAddress(false)
    }
  }

  useEffect(() => {
    if (!addressSearchOpen || !addressSearchRef.current || !window.daum) return
    new window.daum.Postcode({
      width: "100%",
      height: "100%",
      oncomplete: (data) => {
        const address = pickRoadAddress(data)
        setAddressSearchOpen(false)
        if (!isAddressInRegion(address, regionName)) {
          setError(`${regionName} 지역 내 주소만 등록할 수 있어요.`)
          return
        }
        setError(null)
        setBaseAddress(address)
      },
    }).embed(addressSearchRef.current)
  }, [addressSearchOpen])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (!tripId) return
    if (!name.trim()) return setError("장소 이름을 입력해 주세요.")
    if (!baseAddress) return setError("주소 검색을 통해 주소를 선택해 주세요.")

    const address = [baseAddress, detailAddress.trim()].filter(Boolean).join(" ")

    setSubmitting(true)
    try {
      await addCustomPlaceToTrip(tripId, {
        name: name.trim(),
        address,
        visitTime: visitTime || null,
      })
      navigate(`/trips/${tripId}/places`)
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-1 flex-col overflow-hidden">
      <StepHeader title="장소 직접 추가" step={2} totalSteps={3} onBack={() => navigate(-1)} />

      <div className="flex flex-1 flex-col overflow-y-auto px-5">
        <p className="whitespace-pre-line pt-2 text-[12px] leading-[15px] text-ink-soft">
          {"검색 목록에 없는 장소를 직접 등록할 수 있어요. 등록한 장소는 집중도 예측 없이 일정에만 추가돼요."}
        </p>

        <div className="pt-4">
          <FieldLabel required>장소 이름</FieldLabel>
          <TextInput
            placeholder="예) 유성푸르지오시티"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="pt-5">
          <FieldLabel required>주소</FieldLabel>
          <button
            type="button"
            onClick={handleSearchAddress}
            disabled={searchingAddress}
            className="flex h-[52px] w-full items-center gap-2.5 rounded-[var(--radius-field)] border-[0.667px] border-line bg-surface px-4 text-left text-[14px] disabled:opacity-60"
          >
            <Search size={18} className="shrink-0 text-ink-faint" />
            <span className={baseAddress ? "truncate text-ink" : "text-ink-ghost"}>
              {searchingAddress ? "불러오는 중..." : (baseAddress || "주소 검색")}
            </span>
          </button>
          {baseAddress && (
            <TextInput
              className="mt-2"
              placeholder="상세주소 (예: 102동 1301호)"
              value={detailAddress}
              onChange={(e) => setDetailAddress(e.target.value)}
            />
          )}
        </div>

        <div className="pt-5 pb-4">
          <FieldLabel hint="선택">방문 시간</FieldLabel>
          <input
            type="time"
            value={visitTime}
            onChange={(e) => setVisitTime(e.target.value)}
            className="h-[52px] w-full rounded-[var(--radius-field)] border-[0.667px] border-line bg-surface px-4 text-[14px] text-ink outline-none"
          />
        </div>
      </div>

      <div className="border-t-[0.667px] border-line-soft bg-surface/95 px-4 pb-6 pt-3">
        {error && <p className="pb-2 text-center text-[12px] font-medium text-congestion-high">{error}</p>}
        <Button type="submit" block loading={submitting}>
          일정에 추가
        </Button>
      </div>

      {addressSearchOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center">
          <div className="flex h-[70vh] w-full max-w-[420px] flex-col overflow-hidden rounded-t-[var(--radius-banner)] bg-surface sm:rounded-[var(--radius-banner)]">
            <div className="flex items-center justify-between border-b-[0.667px] border-line-soft px-4 py-3">
              <span className="text-[14px] font-bold text-ink">주소 검색</span>
              <button
                type="button"
                onClick={() => setAddressSearchOpen(false)}
                className="rounded-full p-1 text-ink-faint hover:bg-canvas"
              >
                <Close size={18} />
              </button>
            </div>
            <div ref={addressSearchRef} className="flex-1" />
          </div>
        </div>
      )}
    </form>
  )
}
