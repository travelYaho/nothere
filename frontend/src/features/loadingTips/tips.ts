export type LoadingTip = {
  kind: "quiz" | "tip" | "fact"
  text: string
  /** quiz 전용 — "정답 보기"를 눌러야 보인다. */
  answer?: string
}

// 운영시간·요금·규정처럼 바뀔 수 있는 정보는 넣지 않거나, 넣더라도 "확인" 안내를 붙인다.
// 혼잡·한적함을 단정하는 문구는 실제 추천 결과로 오해될 수 있어 쓰지 않는다.
export const COMMON_TIPS: readonly LoadingTip[] = [
  { kind: "tip", text: "계획은 그대로, 한 곳만 “여기 말GO?”" },
  { kind: "tip", text: "일정을 전부 바꿀 필요는 없어요. 원하는 장소만 골라 바꿔 보세요." },
  { kind: "tip", text: "마음에 드는 대안이 없다면, 원래 장소를 유지해도 괜찮아요." },
  { kind: "tip", text: "대안을 고를 때는 장소의 매력과 추가 이동시간을 함께 살펴보세요." },
  { kind: "tip", text: "예상 혼잡도는 방문일 기준 정보예요. 실제 현장 상황과는 다를 수 있어요." },
  { kind: "tip", text: "‘정보 없음’은 ‘한적함’이라는 뜻이 아니에요." },
  { kind: "tip", text: "출발 전 운영시간과 입장 조건도 한 번 더 확인해 보세요." },
]

const SEOUL_TIPS: readonly LoadingTip[] = [
  { kind: "quiz", text: "서울에서 신발을 사라고 권하는 동네는?", answer: "신사동! 신 사, 동!" },
  { kind: "quiz", text: "궁궐 구경하다 투덜대면?", answer: "궁시렁궁시렁!" },
  { kind: "quiz", text: "서울에서 제일 밝은 동네는?", answer: "밝을 명(明) 자를 쓰는 명동!" },
  { kind: "tip", text: "오늘 원하는 건 전시인가요, 산책인가요? 방문 목적을 떠올리면 대안을 고르기 쉬워요." },
  { kind: "tip", text: "서울에 갈 곳은 많고, 내 발걸음은 소중하니까요. 추가 이동시간도 함께 확인해 보세요." },
  { kind: "tip", text: "한복을 입으면 고궁 무료 입장이 가능해요. 한복 기준은 각 궁의 안내를 확인해 보세요." },
  { kind: "tip", text: "경복궁의 정기휴일은 화요일, 창덕궁은 월요일이에요. 공휴일에는 달라질 수 있으니 방문 전 확인하세요." },
  {
    kind: "tip",
    text: "북촌한옥마을 북촌로11길 일대는 관광객 방문 시간이 제한돼요. 가기 전에 종로구 안내를 확인해 보세요.",
  },
  { kind: "fact", text: "한강에 처음 놓인 다리는 1900년에 준공된 한강철교예요." },
  { kind: "fact", text: "매년 12월 31일 자정, 종로 보신각에서 제야의 종을 33번 쳐요." },
]

const BUSAN_TIPS: readonly LoadingTip[] = [
  { kind: "quiz", text: "부산 여행에서 가장 피하고 싶은 일정은?", answer: "너무 부산한 일정!" },
  { kind: "quiz", text: "부산 여행자가 문 앞에서 배고파진 이유는?", answer: "문에 ‘밀면’이라고 적혀 있어서!" },
  {
    kind: "quiz",
    text: "해운대가 늘 운이 좋아 보이는 이유는?",
    answer: "이름에 ‘운’이 있어서! (사실은 구름 운 雲 자예요)",
  },
  { kind: "quiz", text: "부산말 퀴즈! ‘니 단디 해라’는 무슨 뜻일까요?", answer: "‘제대로, 꼼꼼히 해라’라는 뜻이에요." },
  { kind: "tip", text: "바다는 넓고, 우리 일정에도 여유 한 칸쯤." },
  { kind: "tip", text: "지도에서 가까운 곳도 실제 이동은 다를 수 있어요. 앞뒤 동선을 함께 살펴보세요." },
  { kind: "tip", text: "부산은 언덕과 계단이 많은 동네가 많아요. 편한 신발을 추천해요." },
]

export function tipsForRegion(regionName: string | null | undefined): readonly LoadingTip[] {
  if (!regionName) return []
  if (regionName.includes("서울")) return SEOUL_TIPS
  if (regionName.includes("부산")) return BUSAN_TIPS
  return []
}

/** 같은 문구가 연달아 나오지 않게 섞은 새 순서를 만든다(직전에 보여준 문구는 맨 앞에서 뺀다). */
export function shuffledQueue(
  pool: readonly LoadingTip[],
  previous: LoadingTip | null,
  random: () => number = Math.random,
): LoadingTip[] {
  const queue = [...pool]
  for (let i = queue.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1))
    const swap = queue[i]
    queue[i] = queue[j]
    queue[j] = swap
  }
  if (previous && queue.length > 1 && queue[0] === previous) {
    queue.push(queue.shift() as LoadingTip)
  }
  return queue
}
