/**
 * ProfileEditSheet — 마이페이지 "프로필 수정" 바텀시트. 닉네임만 수정한다
 * (프로필 이미지 업로드 인프라는 아직 없다).
 */
import { useEffect, useState } from "react"
import { BottomSheet } from "@/components/feedback/modals"
import { Button } from "@/components/common/primitives"
import { TextInput } from "@/components/common/inputs"

export function ProfileEditSheet({
  open,
  initialNickname,
  saving,
  error,
  onSave,
  onClose,
}: {
  open: boolean
  initialNickname: string
  saving: boolean
  error: string | null
  onSave: (nickname: string) => void
  onClose: () => void
}) {
  const [nickname, setNickname] = useState(initialNickname)

  useEffect(() => {
    if (open) setNickname(initialNickname)
  }, [open, initialNickname])

  const trimmed = nickname.trim()
  const canSave = trimmed.length > 0 && trimmed.length <= 50 && !saving

  return (
    <BottomSheet
      open={open}
      title="프로필 수정"
      onClose={onClose}
      footer={
        <Button
          block
          loading={saving}
          disabled={!canSave}
          onClick={() => onSave(trimmed)}
        >
          저장
        </Button>
      }
    >
      <div className="flex flex-col gap-1.5 pb-2">
        <TextInput
          placeholder="닉네임"
          maxLength={50}
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          autoFocus
        />
        {error && (
          <p className="text-[12px] font-medium text-congestion-high">
            {error}
          </p>
        )}
      </div>
    </BottomSheet>
  )
}
