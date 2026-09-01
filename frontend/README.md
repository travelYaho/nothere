# Frontend

프론트엔드 폴더 구조 및 팀 개발 가이드

## 디렉토리 구조

```text
src/
├── api/                    # Axios 인스턴스, 인터셉터, 공통 에러 처리
├── assets/                 # 이미지, 폰트 등 정적 리소스
├── components/             # 전역 공통 UI 컴포넌트
│   ├── common/             # 버튼, 입력창, 칩, 배지 등
│   ├── layout/             # 헤더, 바텀탭, 레이아웃 컨테이너 등
│   └── feedback/           # 모달, 바텀시트, 토스트, 스피너 등
├── features/               # 도메인별 기능 모듈
│   ├── auth/               # 인증 (로그인/회원가입)
│   ├── schedules/          #   - 여행 일정 관리
│   ├── congestion/         #   - 관광지 혼잡도 분석 및 예측
│   └── recommendation/     #   - 대체 관광지 추천 및 동선 재구성
│       ├── api/            #     - 도메인 전용 API 호출
│       ├── components/     #     - 도메인 전용 UI 컴포넌트
│       ├── hooks/          #     - 도메인 전용 훅
│       ├── types/          #     - 도메인 전용 타입
│       └── index.ts        #     - 외부 공개용 Barrel Export
├── hooks/                  # 범용 공통 훅 (useDebounce 등)
├── pages/                  # 페이지 단위 라우팅 컴포넌트
├── routes/                 # 라우터 설정 및 Protected Route
├── store/                  # 전역 상태 관리 (유저 세션 등)
├── styles/                 # 전역 스타일시트 & Tailwind/디자인 토큰
├── types/                  # 공통 ResponseDTO 및 시스템 타입
└── utils/                  # 공통 유틸리티 함수 (날짜, 포맷터 등)
```

---

## 팀 개발 컨벤션 및 규칙

### 1. `features/{도메인}/` 내부 표준 서브 구조
도메인별 기능 개발 시 아래 서브구조 표준을 준수합니다.
```text
features/{domain-name}/
├── api/          # 해당 도메인의 API 호출 함수 (e.g. schedulesApi.ts)
├── components/   # 해당 도메인 전용 UI 컴포넌트
├── hooks/        # 해당 도메인 전용 커스텀 훅
├── types/        # 해당 도메인 전용 TypeScript 타입 정의
└── index.ts      # 외부(pages 등)로 공개할 요소만 밖으로 노출 (Barrel Export)
```

### 2. `api/` 역할 분리 (전역 vs 도메인)
* **최상위 `src/api/`**: Axios 인스턴스 생성, 토큰 주입 인터셉터, 공통 에러 핸들러 등 **클라이언트 설정**만 담당합니다.
* **`src/features/{domain}/api/`**: 실제 해당 도메인의 REST API 엔드포인트를 호출하는 비즈니스 함수를 관리합니다.

### 3. 전역 vs 도메인 스코프 구분 (`store/`, `hooks/`, `types/`)
* **전역 (`src/store`, `src/hooks`, `src/types`)**: 2개 이상의 도메인에서 공유되는 전역 상태(유저 세션 등), 범용 훅, 공통 Response 타입만 위치시킵니다.
* **도메인 로컬 (`src/features/{domain}/...`)**: 특정 기능 내부에서만 사용되는 상태, 훅, 타입은 해당 도메인 폴더 내부에 둡니다.

### 4. 절대 경로 Alias (`@/`)
절대 경로 Alias가 이미 설정되어 있습니다 (`@/` = `src/`).
- `import { Button } from '@/components/common/Button'`
- `import { useSchedule } from '@/features/schedules/hooks/useSchedule'`
