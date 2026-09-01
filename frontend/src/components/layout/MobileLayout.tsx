/**
 * MobileLayout — 태블릿/데스크톱에서도 모바일 폭(393px)으로 고정해서 보여주는 라우트 레이아웃.
 */
import { Outlet } from "react-router-dom"

export function MobileLayout() {
  return (
    <div className="flex min-h-screen w-full justify-center bg-surface-sunken">
      <div className="flex w-full max-w-[393px] flex-col border-x-[0.667px] border-line-soft bg-canvas">
        <Outlet />
      </div>
    </div>
  )
}
