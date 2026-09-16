/**
 * MyPageView — "마이" 탭 화면.
 * Figma: 여기말GO / node 100:2099 "Container:transform" (마이페이지)
 *
 * 디자인에는 푸시 알림/다크 모드 토글, 공지사항, 고객센터, "교체한 장소"
 * 통계 카드도 있었지만, 관련 백엔드 인프라(FCM, 공지 CMS, 문의 접수)가
 * 없어 범위에서 제외하기로 확정했다 — 위치 권한 설정과 버전 정보만 남긴다.
 */
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Check,
  ChevronRight,
  Heart,
  LogOut,
  MapPin,
  User,
} from "@/components/common/icons"
import { BottomTab, useBottomTabNav } from "@/components/layout/navigation"
import { signOut } from "@/features/auth"
import type { UserResponse } from "@/features/auth/types"
import { getMe, getMyStats, updateNickname } from "@/features/users"
import type { UserStatsResponse } from "@/features/users/types"
import { ProfileEditSheet } from "@/features/users/components/ProfileEditSheet"
import { useLocationPermission } from "@/features/users/hooks/useLocationPermission"
import { ApiError } from "@/types/api"

function toErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  return "정보를 불러오지 못했어요."
}

function SectionLabel({ children }: { children: string }) {
  return (
    <p className="px-1 pb-2 pt-4 text-[12px] font-bold text-ink-faint">
      {children}
    </p>
  )
}

function SettingsRow({
  icon,
  label,
  right,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  right?: React.ReactNode
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className="flex w-full items-center gap-3 px-2 py-3.5 text-left disabled:cursor-default"
    >
      {icon}
      <span className="flex-1 text-[14px] font-semibold text-ink">{label}</span>
      {right}
    </button>
  )
}

const GEO_STATUS_LABEL: Record<string, string> = {
  granted: "허용됨",
  denied: "거부됨",
}

export function MyPageView() {
  const navigate = useNavigate()
  const handleTabChange = useBottomTabNav()

  const [user, setUser] = useState<UserResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [stats, setStats] = useState<UserStatsResponse | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)
  const [statsError, setStatsError] = useState<string | null>(null)

  const [editOpen, setEditOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  const [logoutError, setLogoutError] = useState<string | null>(null)

  const geo = useLocationPermission()

  useEffect(() => {
    let cancelled = false

    setLoading(true)
    setLoadError(null)
    getMe()
      .then((me) => {
        if (!cancelled) setUser(me)
      })
      .catch((err) => {
        if (!cancelled) setLoadError(toErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    setStatsLoading(true)
    setStatsError(null)
    getMyStats()
      .then((myStats) => {
        if (!cancelled) setStats(myStats)
      })
      .catch((err) => {
        if (!cancelled) setStatsError(toErrorMessage(err))
      })
      .finally(() => {
        if (!cancelled) setStatsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  async function handleSaveNickname(nickname: string) {
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await updateNickname(nickname)
      setUser(updated)
      setEditOpen(false)
    } catch (err) {
      setSaveError(toErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleLogout() {
    setLogoutError(null)
    try {
      await signOut()
      navigate("/")
    } catch (err) {
      setLogoutError(toErrorMessage(err))
    }
  }

  return (
    <div className="relative flex flex-1 flex-col">
      <div className="px-5 pb-2.5 pt-2">
        <h1 className="text-[16px] font-extrabold tracking-[-0.32px] text-ink">
          마이
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {loading && (
          <p className="py-10 text-center text-[13px] text-ink-muted">
            불러오는 중...
          </p>
        )}
        {!loading && loadError && (
          <p className="py-10 text-center text-[13px] font-medium text-congestion-high">
            {loadError}
          </p>
        )}

        {!loading && !loadError && user && (
          <>
            <div className="flex items-center gap-3.5 rounded-[var(--radius-field)] bg-surface p-4 shadow-[var(--shadow-card)]">
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[var(--radius-field)] bg-primary/10">
                <User size={26} className="text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[14px] font-extrabold text-ink">
                  {user.nickname}님
                </p>
                <p className="truncate text-[12px] font-medium text-ink-faint">
                  {user.email}
                </p>
              </div>
              <button
                onClick={() => {
                  setSaveError(null)
                  setEditOpen(true)
                }}
                className="shrink-0 rounded-[var(--radius-pill)] border-[0.667px] border-line-chip px-3 py-1.5 text-[12px] font-bold text-ink-soft"
              >
                프로필 수정
              </button>
            </div>

            {statsLoading && (
              <p className="py-4 text-center text-[12px] text-ink-muted">
                통계를 불러오는 중...
              </p>
            )}
            {!statsLoading && statsError && (
              <p className="py-4 text-center text-[12px] font-medium text-congestion-high">
                {statsError}
              </p>
            )}
            {!statsLoading && !statsError && stats && (
              <div className="grid grid-cols-2 gap-2.5 pt-2.5">
                <div className="flex flex-col items-center rounded-[var(--radius-field)] bg-surface p-4 shadow-[var(--shadow-card)]">
                  <span className="text-[20px] font-extrabold text-ink">
                    {stats.totalTripCount}
                  </span>
                  <span className="pt-1 text-[11px] font-medium text-ink-faint">
                    점검한 일정
                  </span>
                </div>
                <div className="flex flex-col items-center rounded-[var(--radius-field)] bg-surface p-4 shadow-[var(--shadow-card)]">
                  <span className="text-[20px] font-extrabold text-ink">
                    {stats.confirmedTripCount}
                  </span>
                  <span className="pt-1 text-[11px] font-medium text-ink-faint">
                    확정 일정
                  </span>
                </div>
              </div>
            )}

            <SectionLabel>활동</SectionLabel>
            <div className="rounded-[var(--radius-field)] bg-surface px-2 shadow-[var(--shadow-card)]">
              <SettingsRow
                icon={<Heart size={18} className="text-primary" />}
                label="좋아요한 가이드북"
                right={<ChevronRight size={16} className="text-ink-faint" />}
                onClick={() => navigate("/guides/liked")}
              />
            </div>

            <SectionLabel>설정</SectionLabel>
            <div className="rounded-[var(--radius-field)] bg-surface px-2 shadow-[var(--shadow-card)]">
              <SettingsRow
                icon={<MapPin size={18} className="text-ink-soft" />}
                label="위치 권한 설정"
                right={
                  geo.state === "granted" || geo.state === "denied" ? (
                    <span
                      className={[
                        "text-[12px] font-semibold",
                        geo.state === "granted"
                          ? "text-congestion-low"
                          : "text-congestion-high",
                      ].join(" ")}
                    >
                      {GEO_STATUS_LABEL[geo.state]}
                    </span>
                  ) : (
                    <ChevronRight size={16} className="text-ink-faint" />
                  )
                }
                onClick={geo.request}
              />
            </div>
            {geo.message && (
              <p className="px-2 pt-2 text-[12px] leading-[17px] font-medium text-ink-soft">
                {geo.message}{" "}
                <button
                  onClick={geo.clearMessage}
                  className="font-bold text-ink-faint underline"
                >
                  닫기
                </button>
              </p>
            )}

            <SectionLabel>지원</SectionLabel>
            <div className="rounded-[var(--radius-field)] bg-surface px-2 shadow-[var(--shadow-card)]">
              <SettingsRow
                icon={<Check size={18} className="text-ink-soft" />}
                label="버전 정보"
                right={
                  <span className="text-[12px] font-medium text-ink-faint">
                    1.0.0
                  </span>
                }
              />
            </div>

            <button
              onClick={() => void handleLogout()}
              className="mt-4 flex h-[52px] w-full items-center justify-center gap-2 rounded-[var(--radius-field)] bg-surface shadow-[var(--shadow-card)]"
            >
              <LogOut size={18} className="text-congestion-high" />
              <span className="text-[14px] font-bold text-congestion-high">
                로그아웃
              </span>
            </button>
            {logoutError && (
              <p className="pt-2 text-center text-[12px] font-medium text-congestion-high">
                {logoutError}
              </p>
            )}
          </>
        )}
      </div>

      <BottomTab active="my" onChange={handleTabChange} />

      {user && (
        <ProfileEditSheet
          open={editOpen}
          initialNickname={user.nickname}
          saving={saving}
          error={saveError}
          onSave={(nickname) => void handleSaveNickname(nickname)}
          onClose={() => setEditOpen(false)}
        />
      )}
    </div>
  )
}
