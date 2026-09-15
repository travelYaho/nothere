import { useCallback, useEffect, useRef, useState, type PointerEvent } from "react"

const LONG_PRESS_MS = 350

type PointerPos = { x: number; y: number }

/**
 * 드래그 순서변경은 HTML5 네이티브 draggable 대신 포인터 이벤트로 직접
 * 구현했다 — 네이티브 drag&drop 은 터치스크린(모바일)에서 아예 동작하지
 * 않고, 데스크톱에서도 "누르고만 있기"로는 시작되지 않아 "길게 눌러 순서
 * 변경" UX와 맞지 않는다. 손잡이(Grip)를 일정 시간 누르고 있으면 드래그가
 * 시작되고, setPointerCapture 덕분에 손가락/마우스가 손잡이 밖으로 나가도
 * move/up 이벤트를 계속 받는다.
 */
export function useLongPressReorder(onReorder: (fromIndex: number, toIndex: number) => void) {
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [overIndex, setOverIndex] = useState<number | null>(null)
  const [pointerPos, setPointerPos] = useState<PointerPos | null>(null)

  const dragIndexRef = useRef<number | null>(null)
  const overIndexRef = useRef<number | null>(null)
  const onReorderRef = useRef(onReorder)
  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  onReorderRef.current = onReorder

  useEffect(() => {
    return () => {
      if (longPressTimer.current !== null) clearTimeout(longPressTimer.current)
    }
  }, [])

  function clearLongPressTimer() {
    if (longPressTimer.current !== null) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
  }

  function resetDrag() {
    dragIndexRef.current = null
    overIndexRef.current = null
    setDragIndex(null)
    setOverIndex(null)
    setPointerPos(null)
  }

  const handlePointerDown = useCallback((index: number) => {
    return (e: PointerEvent<Element>) => {
      e.currentTarget.setPointerCapture(e.pointerId)
      clearLongPressTimer()
      const { clientX, clientY } = e
      longPressTimer.current = setTimeout(() => {
        dragIndexRef.current = index
        overIndexRef.current = index
        setDragIndex(index)
        setOverIndex(index)
        setPointerPos({ x: clientX, y: clientY })
      }, LONG_PRESS_MS)
    }
  }, [])

  const handlePointerMove = useCallback((e: PointerEvent<Element>) => {
    if (dragIndexRef.current === null) return
    setPointerPos({ x: e.clientX, y: e.clientY })
    const el = document.elementFromPoint(e.clientX, e.clientY)
    const rowEl = el instanceof Element ? el.closest<HTMLElement>("[data-row-index]") : null
    if (!rowEl) return
    const idx = Number(rowEl.dataset.rowIndex)
    if (Number.isNaN(idx)) return
    overIndexRef.current = idx
    setOverIndex(idx)
  }, [])

  const handlePointerUp = useCallback(() => {
    clearLongPressTimer()
    const from = dragIndexRef.current
    const to = overIndexRef.current
    if (from !== null && to !== null && from !== to) {
      onReorderRef.current(from, to)
    }
    resetDrag()
  }, [])

  const handlePointerCancel = useCallback(() => {
    clearLongPressTimer()
    resetDrag()
  }, [])

  function gripProps(index: number) {
    return {
      onPointerDown: handlePointerDown(index),
      onPointerMove: handlePointerMove,
      onPointerUp: handlePointerUp,
      onPointerCancel: handlePointerCancel,
      style: { touchAction: "none" as const },
    }
  }

  return {
    dragIndex,
    overIndex,
    pointerPos,
    gripProps,
    isDragging: (index: number) => dragIndex === index,
    isDropTarget: (index: number) => dragIndex !== null && overIndex === index && dragIndex !== index,
  }
}
