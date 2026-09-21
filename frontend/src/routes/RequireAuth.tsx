/**
 * 회원 전용 라우트 가드. 세션이 없으면 보호된 화면을 그리지 않고 로그인으로 보낸다.
 * 세션 확인 전에는 스피너만 보여 토큰 없음 에러가 깜빡이지 않게 한다.
 */
import { Navigate, Outlet, useLocation } from "react-router-dom"
import { Spinner } from "@/components/common/primitives"
import { useSession } from "@/store/sessionStore"

export function RequireAuth() {
  const { session, isLoading } = useSession()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Spinner />
      </div>
    )
  }

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}
