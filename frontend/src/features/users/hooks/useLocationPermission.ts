/**
 * 위치 권한 상태 조회 + 재요청 훅.
 *
 * PC 브라우저는 아직 결정 안 한(prompt) 상태에서 getCurrentPosition 을 호출하면
 * 네이티브 권한 팝업이 뜬다. 반면 모바일 브라우저는 한 번 거부(denied)하면
 * 코드로 다시 팝업을 띄울 수 없어 사용자가 폰 설정 앱에서 직접 허용해야
 * 한다 — 그래서 denied 상태에서는 안내 메시지만 보여준다.
 */
import { useEffect, useState } from "react"

export type GeoPermissionState = "granted" | "denied" | "prompt" | "unsupported"

export function useLocationPermission() {
  const [state, setState] = useState<GeoPermissionState>("unsupported")
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    if (!("permissions" in navigator)) return
    let status: PermissionStatus | null = null
    navigator.permissions
      .query({ name: "geolocation" })
      .then((result) => {
        status = result
        setState(result.state as GeoPermissionState)
        result.onchange = () => setState(result.state as GeoPermissionState)
      })
      .catch(() => {})
    return () => {
      if (status) status.onchange = null
    }
  }, [])

  function request() {
    setMessage(null)
    if (!("geolocation" in navigator)) {
      setMessage("이 브라우저는 위치 정보를 지원하지 않아요.")
      return
    }
    navigator.geolocation.getCurrentPosition(
      () => {
        setState("granted")
        setMessage("위치 권한이 허용되어 있어요.")
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setState("denied")
          setMessage(
            "위치 권한이 거부되어 있어요. PC는 주소창의 자물쇠 아이콘에서, 휴대폰은 설정 앱의 앱 권한 메뉴에서 허용해 주세요.",
          )
        } else {
          setMessage(
            "위치 정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요.",
          )
        }
      },
      { timeout: 8000 },
    )
  }

  return { state, message, request, clearMessage: () => setMessage(null) }
}
