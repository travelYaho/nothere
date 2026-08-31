/**
 * 모달 틀 2종 — 앱 전체 재사용.
 *
 *  AlertDialog (팝업형): 제목 + 설명 + 취소/확인.
 *    → 삭제확인 · 이탈확인 · 임시저장확인 · 일정확정완료 · 에러재시도
 *      전부 이 틀에 텍스트/tone만 바꿔 사용.
 *
 *  BottomSheet (바텀시트형): 둥근 모서리 + 드래그핸들 + 슬라이드업 공통.
 *    → 날짜선택 · 지역선택 · 조건수정 · 대안교체확인
 *      각 내용은 children 슬롯으로 채움.
 *
 * 데모/갤러리에서는 부모(relative) 안에 absolute로 오버레이합니다.
 * 실제 앱에서는 portal + fixed 로 감싸면 됩니다.
 */
import type { ReactNode } from "react"
import { Button } from "./primitives"

function Scrim({ onClick }: { onClick?: () => void }) {
  return (
    <button
      aria-label="닫기"
      onClick={onClick}
      className="absolute inset-0 z-40 animate-fade-in bg-ink/45"
    />
  )
}

/* ------------------------------------------------------------------ */
/* AlertDialog                                                         */
/* ------------------------------------------------------------------ */
export function AlertDialog({
  open,
  title,
  description,
  confirmLabel = "확인",
  cancelLabel = "취소",
  tone = "default",
  hideCancel = false,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  description?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  tone?: "default" | "danger" | "success"
  hideCancel?: boolean
  onConfirm?: () => void
  onCancel?: () => void
}) {
  if (!open) return null
  const confirmClass =
    tone === "danger"
      ? "!bg-congestion-high /* shadow-[0_4px_8px_rgba(221,64,64,0.28)] */"
      : ""
  return (
    <>
      <Scrim onClick={onCancel} />
      <div className="absolute inset-0 z-50 flex items-center justify-center px-8">
        <div
          role="alertdialog"
          className="w-full max-w-[320px] animate-pop-in rounded-[var(--radius-banner)] border-[0.667px] border-line bg-surface p-6 text-center /* shadow-[0_24px_48px_rgba(16,24,48,0.28)] */"
        >
          <h2 className="text-[17px] font-extrabold tracking-[-0.34px] text-ink">{title}</h2>
          {description && (
            <p className="mt-2 text-[13px] leading-[19.5px] text-ink-soft">{description}</p>
          )}
          <div className="mt-5 flex gap-2.5">
            {!hideCancel && (
              <Button variant="ghost" block onClick={onCancel} className="text-[15px] font-bold">
                {cancelLabel}
              </Button>
            )}
            <Button block onClick={onConfirm} className={confirmClass}>
              {confirmLabel}
            </Button>
          </div>
        </div>
      </div>
    </>
  )
}

/* ------------------------------------------------------------------ */
/* BottomSheet                                                         */
/* ------------------------------------------------------------------ */
export function BottomSheet({
  open,
  title,
  children,
  footer,
  onClose,
}: {
  open: boolean
  title?: string
  children: ReactNode
  footer?: ReactNode
  onClose?: () => void
}) {
  if (!open) return null
  return (
    <>
      <Scrim onClick={onClose} />
      <div className="absolute inset-x-0 bottom-0 z-50 flex flex-col">
        <div className="animate-sheet-up rounded-t-[var(--radius-banner)] bg-surface shadow-[var(--shadow-sheet)]">
          <div className="flex justify-center pt-2.5">
            <span className="h-1 w-10 rounded-full bg-[#d3dbe6]" />
          </div>
          {title && (
            <h2 className="px-5 pb-1 pt-3 text-[16px] font-extrabold tracking-[-0.32px] text-ink">
              {title}
            </h2>
          )}
          <div className="max-h-[60vh] overflow-y-auto px-5 pb-2 pt-2">{children}</div>
          {footer && (
            <div className="border-t-[0.667px] border-line-soft px-4 pb-6 pt-3">{footer}</div>
          )}
        </div>
      </div>
    </>
  )
}
