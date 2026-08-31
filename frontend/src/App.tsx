import { useState } from "react"
import { ArrowRight, Bell, MapPin, Plus } from "./components/common/icons"
import { Button, Chip, CongestionBadge, type CongestionLevel } from "./components/common/primitives"
import {
  DatePicker,
  FieldLabel,
  PasswordInput,
  SearchBar,
  Select,
  TextArea,
  TextInput,
} from "./components/common/inputs"
import {
  BannerCard,
  ChangeLogItem,
  CongestionCard,
  RecommendCard,
  ScheduleCard,
  SearchResultItem,
} from "./components/common/cards"
import { BasicHeader, BottomTab, FlowHeader, StatusBar } from "./components/layout/navigation"
import { AlertDialog, BottomSheet } from "./components/feedback/modals"


/* ── 갤러리 레이아웃 헬퍼 ─────────────────────────────────────── */
function Section({
  id,
  title,
  desc,
  children,
}: {
  id: string
  title: string
  desc?: string
  children: React.ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-6">
      <div className="mb-4">
        <h2 className="text-[19px] font-extrabold tracking-[-0.4px] text-ink">{title}</h2>
        {desc && <p className="mt-1 text-[13px] leading-[19px] text-ink-muted">{desc}</p>}
      </div>
      {children}
    </section>
  )
}

function Case({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
        {label}
      </span>
      <div className="flex flex-wrap items-start gap-3">{children}</div>
    </div>
  )
}

function Panel({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-[var(--radius-banner)] border-[0.667px] border-line-soft bg-surface p-6 shadow-[var(--shadow-card)]">
      {children}
    </div>
  )
}

/** 모달 데모용 미니 폰 프레임 (relative 컨테이너) */
function PhoneStage({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative h-[420px] w-full max-w-[300px] overflow-hidden rounded-[32px] border-[0.667px] border-line bg-canvas">
      <StatusBar />
      <div className="px-4 pt-2">
        <p className="text-[13px] font-medium text-ink-muted">
          모달 미리보기 스테이지 — 버튼을 눌러 열어보세요.
        </p>
      </div>
      {children}
    </div>
  )
}

const NAV = [
  ["tokens", "파운데이션"],
  ["buttons", "버튼"],
  ["chips", "칩"],
  ["inputs", "입력"],
  ["badges", "혼잡도"],
  ["cards", "카드"],
  ["nav", "헤더·네비"],
  ["modals", "모달"],
] as const

/* ── 파운데이션: 토큰 스와치 ─────────────────────────────────── */
const COLOR_TOKENS: { name: string; token: string; value: string; on?: string }[] = [
  { name: "primary", token: "--color-primary", value: "#3A8F60", on: "#fff" },
  { name: "ink", token: "--color-ink", value: "#0d1117", on: "#fff" },
  { name: "ink-soft", token: "--color-ink-soft", value: "#4a5568", on: "#fff" },
  { name: "ink-faint", token: "--color-ink-faint", value: "#9ba8b8", on: "#fff" },
  { name: "canvas", token: "--color-canvas", value: "#f4f6fb" },
  { name: "surface", token: "--color-surface", value: "#ffffff" },
  { name: "line", token: "--color-line", value: "#e0e6ef" },
]
const CONGESTION_TOKENS: { level: CongestionLevel; name: string; value: string }[] = [
  { level: "high", name: "congestion-high", value: "#dd4040" },
  { level: "medium", name: "congestion-medium", value: "#c99a2e" },
  { level: "low", name: "congestion-low", value: "#22a565" },
  { level: "none", name: "congestion-none", value: "#9ba8b8" },
]

export default function App() {
  // 인터랙션 상태값 데모
  const [single, setSingle] = useState("친구")
  const [multi, setMulti] = useState<string[]>(["자연·산책", "역사·문화"])
  const [region, setRegion] = useState("서울")
  const [date, setDate] = useState<Date | undefined>(new Date(2026, 7, 15))
  const [tab, setTab] = useState("home")
  const [added, setAdded] = useState(false)

  // 모달 상태
  const [dialog, setDialog] = useState<null | "delete" | "leave" | "save" | "done" | "error">(null)
  const [sheet, setSheet] = useState<null | "date" | "region" | "condition" | "swap">(null)

  const dialogProps = {
    delete: {
      title: "이 일정을 삭제할까요?",
      description: "삭제하면 되돌릴 수 없어요.",
      confirmLabel: "삭제",
      tone: "danger" as const,
    },
    leave: {
      title: "작성 중인 내용이 있어요",
      description: "지금 나가면 입력한 조건이 사라집니다.",
      confirmLabel: "나가기",
      tone: "danger" as const,
    },
    save: {
      title: "임시 저장할까요?",
      description: "보관함에서 이어서 점검할 수 있어요.",
      confirmLabel: "임시 저장",
    },
    done: {
      title: "일정이 확정됐어요",
      description: "혼잡 예상 2곳을 여유로운 대안으로 바꿨어요.",
      confirmLabel: "확인",
      tone: "success" as const,
      hideCancel: true,
    },
    error: {
      title: "대안을 불러오지 못했어요",
      description: "네트워크 상태를 확인하고 다시 시도해주세요.",
      confirmLabel: "다시 시도",
      cancelLabel: "닫기",
    },
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      {/* 헤더 */}
      <header className="sticky top-0 z-30 border-b-[0.667px] border-line-soft bg-canvas/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1080px] items-center justify-between px-6 py-4">
          <div>
            <p className="text-[11px] font-bold tracking-[0.88px] text-primary">
              DESIGN SYSTEM
            </p>
            <h1 className="text-[20px] font-extrabold tracking-[-0.5px] text-ink">
              여기말고 — 컴포넌트 & 파운데이션
            </h1>
          </div>
          <nav className="hidden gap-1 md:flex">
            {NAV.map(([id, label]) => (
              <a
                key={id}
                href={`#${id}`}
                className="rounded-full px-3 py-1.5 text-[13px] font-semibold text-ink-soft transition-colors hover:bg-surface hover:text-primary"
              >
                {label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto flex max-w-[1080px] flex-col gap-16 px-6 py-12">
        {/* 파운데이션 */}
        <Section id="tokens" title="파운데이션">
          <div className="grid gap-6 md:grid-cols-2">
            <Panel>
              <p className="mb-4 text-[13px] font-bold text-ink">색상</p>
              <div className="grid grid-cols-2 gap-3">
                {COLOR_TOKENS.map((c) => (
                  <div key={c.name} className="flex items-center gap-3">
                    <span
                      className="h-11 w-11 shrink-0 rounded-[12px] border-[0.667px] border-line"
                      style={{ background: c.value }}
                    />
                    <span className="min-w-0">
                      <span className="block truncate text-[13px] font-bold text-ink">
                        {c.name}
                      </span>
                      <span className="block truncate text-[11px] text-ink-faint">{c.value}</span>
                    </span>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel>
              <p className="mb-4 text-[13px] font-bold text-ink">혼잡도 시맨틱 (서비스 핵심)</p>
              <div className="flex flex-col gap-3">
                {CONGESTION_TOKENS.map((c) => (
                  <div key={c.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span
                        className="h-6 w-6 rounded-full"
                        style={{ background: c.value }}
                      />
                      <span className="text-[12px] text-ink-faint">{c.name}</span>
                    </div>
                    <CongestionBadge level={c.level} />
                  </div>
                ))}
              </div>
            </Panel>

            <Panel>
              <p className="mb-4 text-[13px] font-bold text-ink">타이포 (Pretendard)</p>
              <div className="flex flex-col gap-2.5">
                <p className="text-[24px] font-extrabold tracking-[-0.63px]">Display 24 · 여기말고</p>
                <p className="text-[19px] font-extrabold tracking-[-0.4px]">Title 19 · 일정 점검</p>
                <p className="text-[16px] font-extrabold">Heading 16 · 대안 찾기</p>
                <p className="text-[14px] font-bold">Body 14 · 경복궁 관람</p>
                <p className="text-[13px] font-medium text-ink-soft">Label 13 · 방문 지역</p>
                <p className="text-[11px] font-medium text-ink-faint">Micro 11 · 4곳 등록</p>
              </div>
            </Panel>

            <Panel>
              <p className="mb-4 text-[13px] font-bold text-ink">라운드 · 그림자</p>
              <div className="flex flex-wrap items-end gap-4">
                <div className="text-center">
                  <span className="mb-2 block h-16 w-16 rounded-[16px] border border-line-soft bg-surface shadow-[var(--shadow-card)]" />
                  <span className="text-[11px] text-ink-faint">field 16 · card</span>
                </div>
                <div className="text-center">
                  <span className="mb-2 block h-16 w-16 rounded-[24px] border border-line-soft bg-surface shadow-[var(--shadow-card)]" />
                  <span className="text-[11px] text-ink-faint">banner 24</span>
                </div>
                <div className="text-center">
                  <span className="mb-2 block h-16 w-16 rounded-full border border-line-soft bg-surface shadow-[var(--shadow-card)]" />
                  <span className="text-[11px] text-ink-faint">pill</span>
                </div>
                <div className="text-center">
                  <span className="mb-2 block h-16 w-16 rounded-[16px] bg-primary shadow-[var(--shadow-primary-soft)]" />
                  <span className="text-[11px] text-ink-faint">primary</span>
                </div>
              </div>
            </Panel>
          </div>
        </Section>

        {/* 버튼 */}
        <Section id="buttons" title="버튼" desc="primary · ghost · text / 상태: default · loading · disabled">
          <Panel>
            <div className="flex flex-col gap-6">
              <Case label="primary">
                <Button leadingIcon={<Plus size={16} />}>새 일정 점검하기</Button>
                <Button loading>로딩중</Button>
                <Button disabled>비활성</Button>
              </Case>
              <Case label="ghost">
                <Button variant="ghost">임시 저장</Button>
                <Button variant="ghost" disabled>비활성</Button>
              </Case>
              <Case label="text">
                <Button variant="text">더보기</Button>
                <Button variant="text">조건 수정</Button>
              </Case>
              <Case label="block (전체너비)">
                <div className="w-full max-w-[341px]">
                  <Button block leadingIcon={<Plus size={16} />}>
                    여행 조건 등록
                  </Button>
                </div>
              </Case>
            </div>
          </Panel>
        </Section>

        {/* 칩 */}
        <Section
          id="chips"
          title="칩"
          desc="single(단일선택) — 동행유형처럼 하나만 / multi(다중선택) — 선호경험처럼 여러 개"
        >
          <div className="grid gap-6 md:grid-cols-2">
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">
                single <span className="font-medium text-ink-faint">· 선택: {single}</span>
              </p>
              <div className="flex flex-wrap gap-2">
                {["혼자", "연인", "친구", "가족"].map((c) => (
                  <Chip
                    key={c}
                    label={c}
                    variant="single"
                    selected={single === c}
                    onClick={() => setSingle(c)}
                  />
                ))}
                <Chip label="비활성" disabled />
              </div>
            </Panel>
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">
                multi <span className="font-medium text-ink-faint">· 선택 {multi.length}개</span>
              </p>
              <div className="flex flex-wrap gap-2">
                {["자연·산책", "역사·문화", "건축·공간", "사진·전망", "음식·시장", "카페·휴식"].map(
                  (c) => (
                    <Chip
                      key={c}
                      label={c}
                      variant="multi"
                      selected={multi.includes(c)}
                      onClick={() =>
                        setMulti((prev) =>
                          prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c],
                        )
                      }
                    />
                  ),
                )}
              </div>
            </Panel>
          </div>
        </Section>

        {/* 입력 */}
        <Section
          id="inputs"
          title="입력"
          desc="TextInput · Password · Select · TextArea · SearchBar · DatePicker / focus·filled·error·disabled"
        >
          <div className="grid gap-6 md:grid-cols-2">
            <Panel>
              <FieldLabel required>이메일</FieldLabel>
              <TextInput placeholder="이메일" defaultValue="trip@yeogimalgo.app" />
              <div className="h-4" />
              <FieldLabel required>비밀번호</FieldLabel>
              <PasswordInput placeholder="비밀번호" defaultValue="password" />
              <div className="h-4" />
              <FieldLabel>에러 상태</FieldLabel>
              <TextInput placeholder="이메일" defaultValue="wrong@" error="이메일 형식을 확인해주세요." />
            </Panel>
            <Panel>
              <FieldLabel required>방문 지역</FieldLabel>
              <Select
                value={region}
                options={["서울", "부산", "전주", "경주", "제주"]}
                onChange={setRegion}
              />
              <div className="h-4" />
              <FieldLabel required>여행 날짜</FieldLabel>
              <DatePicker value={date} onChange={setDate} />
              <div className="h-4" />
              <FieldLabel>검색</FieldLabel>
              <SearchBar />
            </Panel>
            <Panel>
              <FieldLabel hint="(선택)">추가 요청</FieldLabel>
              <TextArea placeholder="예) 한옥이 있는 골목에서 사진을 찍고 싶어요" rows={3} />
            </Panel>
            <Panel>
              <FieldLabel>비활성 상태</FieldLabel>
              <TextInput placeholder="입력 불가" disabled />
              <div className="h-4" />
              <Select value="종로구" options={["종로구", "중구"]} disabled />
            </Panel>
          </div>
        </Section>

        {/* 혼잡도 뱃지 */}
        <Section id="badges" title="혼잡도 뱃지" desc="방문 추이 기반 예측 정보. 색상만으로 구분하지 않고 라벨을 함께 노출합니다.">
          <Panel>
            <div className="flex flex-wrap gap-6">
              <CongestionBadge level="high" />
              <CongestionBadge level="medium" />
              <CongestionBadge level="low" />
              <CongestionBadge level="none" />
            </div>
          </Panel>
        </Section>

        {/* 카드 */}
        <Section id="cards" title="카드" desc="일정 · 혼잡경고 · 추천 · 검색결과 · 배너 · 변경기록">
          <div className="grid gap-6 md:grid-cols-2">
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">ScheduleCard</p>
              <div className="flex flex-col gap-2.5">
                <ScheduleCard index={1} title="서울 서촌 당일치기" meta="2026년 8월 14일 | 4곳 등록" active />
                <ScheduleCard index={2} title="전주 당일치기" meta="2026년 8월 12일 | 4곳 등록" />
              </div>
            </Panel>
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">CongestionCard</p>
              <div className="flex flex-col gap-2.5">
                <CongestionCard time="10:00" place="경복궁" level="high" />
                <CongestionCard time="12:00" place="통인시장" level="medium" />
                <CongestionCard time="14:00" place="서촌" level="none" />
              </div>
            </Panel>
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">RecommendCard · SearchResultItem</p>
              <div className="grid grid-cols-2 gap-2.5">
                <RecommendCard tag="TODAY'S PICK" title="유성온천" level="low" />
                <RecommendCard tag="추천" title="창덕궁 후원" level="low" />
              </div>
              <div className="mt-2.5 flex flex-col gap-2.5">
                <SearchResultItem name="북촌한옥마을" category="관광 · 종로구" added={added} onAdd={() => setAdded(true)} />
                <SearchResultItem name="국립현대미술관" category="전시 · 종로구" added />
              </div>
            </Panel>
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">ChangeLogItem</p>
              <div className="flex flex-col gap-2.5">
                <ChangeLogItem from="경복궁" fromLevel="high" to="창덕궁 후원" toLevel="low" />
                <ChangeLogItem from="남산서울타워" fromLevel="high" to="낙산공원" toLevel="low" />
              </div>
            </Panel>
            <div className="md:col-span-2">
              <Panel>
                <p className="mb-3 text-[13px] font-bold text-ink">BannerCard</p>
                <div className="grid gap-4 md:grid-cols-2">
                  <BannerCard
                    eyebrow="TRAVEL SMART"
                    title={<>새로운 장소에서<br />새로운 기회를 찾아봐요</>}
                    subtitle="여기말GO가 숨은 명소를 알려드릴게요. 함께 출발해볼까요?"
                    imageUrl="https://images.unsplash.com/photo-1538485399081-7191377e8241?w=680&h=420&fit=crop&auto=format"
                  />
                  <BannerCard
                    tone="warn"
                    eyebrow="일정 혼잡 예상"
                    title="일정 점검이 필요해요"
                    subtitle="현재 등록된 장소가 혼잡할 것으로 예상돼요. 매력 넘치는 다른 장소를 추천해드릴게요."
                    imageUrl="https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=680&h=420&fit=crop&auto=format"
                  />
                </div>
              </Panel>
            </div>
          </div>
        </Section>

        {/* 헤더·네비 */}
        <Section id="nav" title="헤더 · 네비게이션" desc="BasicHeader · FlowHeader(진행바) · BottomTab">
          <div className="grid gap-6 md:grid-cols-2">
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">BasicHeader</p>
              <div className="overflow-hidden rounded-[16px] border-[0.667px] border-line bg-canvas">
                <BasicHeader
                  title="일정 점검 결과"
                  onBack={() => { }}
                  right={<button className="text-[13px] font-bold text-primary">일정 수정</button>}
                />
              </div>
              <p className="mb-3 mt-5 text-[13px] font-bold text-ink">FlowHeader</p>
              <div className="overflow-hidden rounded-[16px] border-[0.667px] border-line bg-canvas">
                <FlowHeader
                  title="여행 조건"
                  step={1}
                  totalSteps={3}
                  progress={0.33}
                  onBack={() => { }}
                  subline={
                    <p className="pl-8 text-[12px] font-medium text-ink-muted">
                      08.15 (토) · 서울 종로구 · 친구
                    </p>
                  }
                />
              </div>
            </Panel>
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">BottomTab</p>
              <div className="overflow-hidden rounded-[16px] border-[0.667px] border-line">
                <BottomTab active={tab} onChange={setTab} />
              </div>
              <p className="mt-3 text-[12px] text-ink-muted">현재 탭: {tab}</p>
              <div className="mt-5 flex items-center gap-3">
                <span className="text-[13px] font-bold text-ink">헤더 우측 아이콘</span>
                <MapPin size={20} className="text-ink-soft" />
                <Bell size={20} className="text-ink-soft" />
                <ArrowRight size={20} className="text-ink-soft" />
              </div>
            </Panel>
          </div>
        </Section>

        {/* 모달 */}
        <Section
          id="modals"
          title="모달"
          desc="AlertDialog(팝업 1틀, 5케이스) + BottomSheet(바텀시트 1틀, 4콘텐츠). 스테이지 안에서 열립니다."
        >
          <div className="grid gap-6 md:grid-cols-2">
            {/* AlertDialog */}
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">AlertDialog — 텍스트만 스왑</p>
              <div className="mb-4 flex flex-wrap gap-2">
                {(["delete", "leave", "save", "done", "error"] as const).map((k) => (
                  <Button key={k} variant="ghost" onClick={() => setDialog(k)}>
                    {{ delete: "삭제확인", leave: "이탈확인", save: "임시저장", done: "확정완료", error: "에러재시도" }[k]}
                  </Button>
                ))}
              </div>
              <PhoneStage>
                {dialog && (
                  <AlertDialog
                    open
                    {...dialogProps[dialog]}
                    onConfirm={() => setDialog(null)}
                    onCancel={() => setDialog(null)}
                  />
                )}
              </PhoneStage>
            </Panel>

            {/* BottomSheet */}
            <Panel>
              <p className="mb-3 text-[13px] font-bold text-ink">BottomSheet — 콘텐츠 슬롯</p>
              <div className="mb-4 flex flex-wrap gap-2">
                {(["date", "region", "condition", "swap"] as const).map((k) => (
                  <Button key={k} variant="ghost" onClick={() => setSheet(k)}>
                    {{ date: "날짜선택", region: "지역선택", condition: "조건수정", swap: "대안교체" }[k]}
                  </Button>
                ))}
              </div>
              <PhoneStage>
                <BottomSheet
                  open={sheet === "date"}
                  title="여행 날짜 선택"
                  onClose={() => setSheet(null)}
                  footer={<Button block onClick={() => setSheet(null)}>적용</Button>}
                >
                  <DatePicker value={date} onChange={setDate} />
                  <div className="h-2" />
                </BottomSheet>

                <BottomSheet
                  open={sheet === "region"}
                  title="방문 지역 선택"
                  onClose={() => setSheet(null)}
                >
                  <div className="flex flex-wrap gap-2 pb-3">
                    {["서울", "부산", "전주", "경주", "제주", "강릉"].map((r) => (
                      <Chip key={r} label={r} selected={region === r} onClick={() => setRegion(r)} />
                    ))}
                  </div>
                </BottomSheet>

                <BottomSheet
                  open={sheet === "condition"}
                  title="여행 조건 수정"
                  onClose={() => setSheet(null)}
                  footer={<Button block onClick={() => setSheet(null)}>조건 적용</Button>}
                >
                  <FieldLabel required>동행 유형</FieldLabel>
                  <div className="flex flex-wrap gap-2 pb-4">
                    {["혼자", "연인", "친구", "가족"].map((c) => (
                      <Chip key={c} label={c} selected={single === c} onClick={() => setSingle(c)} />
                    ))}
                  </div>
                  <FieldLabel required>여행 날짜</FieldLabel>
                  <DatePicker value={date} onChange={setDate} />
                  <div className="h-2" />
                </BottomSheet>

                <BottomSheet
                  open={sheet === "swap"}
                  title="이 장소로 바꿀까요?"
                  onClose={() => setSheet(null)}
                  footer={
                    <div className="flex gap-2.5">
                      <Button variant="ghost" onClick={() => setSheet(null)} className="w-[92px] shrink-0 font-bold">
                        유지
                      </Button>
                      <Button block onClick={() => setSheet(null)}>대안으로 교체</Button>
                    </div>
                  }
                >
                  <div className="pb-2">
                    <ChangeLogItem from="경복궁" fromLevel="high" to="창덕궁 후원" toLevel="low" />
                    <p className="mt-3 text-[12px] leading-[18px] text-ink-muted">
                      현재 위치에서 3km 이내, 비슷한 경험을 즐길 수 있는 여유로운 장소예요.
                    </p>
                  </div>
                </BottomSheet>
              </PhoneStage>
            </Panel>
          </div>
        </Section>

        <footer className="border-t-[0.667px] border-line-soft pt-8 text-[12px] text-ink-faint">
          여기말고 디자인 시스템 · 토큰은 <code className="text-ink-soft">src/index.css</code>, 컴포넌트는{" "}
          <code className="text-ink-soft">src/components/</code> 에 있습니다.
        </footer>
      </main>
    </div>
  )
}
