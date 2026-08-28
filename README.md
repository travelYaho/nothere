# 여기말GO

웹 기반 여행 일정 수정 서비스입니다. 기존 여행 일정을 등록하면 관광지 집중도 예측을 분석하고, 혼잡이 예상되는 장소를 조건·취향에 맞는 대체 관광지로 교체할 수 있도록 지원합니다.


## 구조

```text
yeogimalgo/
├── frontend/                     # 프론트엔드 (스켈레톤)
│   ├── public/
│   └── src/
└── backend/                      # FastAPI + SQLAlchemy + Alembic + Supabase
    ├── app/
    │   ├── api/                  # HTTP 엔드포인트
    │   ├── core/                 # 설정, JWT 검증, 예외
    │   ├── db/                   # 세션 + ORM 모델
    │   ├── repositories/         # DB CRUD
    │   ├── schemas/              # 요청/응답 Pydantic
    │   ├── services/             # 비즈니스 로직 (1주차: auth/users/home)
    │   ├── clients/              # 외부 API (관광, LLM 등)
    │   ├── domains/              # 기능별 담당 코드
    │   │   ├── schedules/
    │   │   ├── recommendation/
    │   │   └── ai/
    │   └── utils/
    ├── alembic/
    ├── supabase/
    └── tests/
```


백엔드 실행·환경변수·Swagger: [backend/README.md](backend/README.md)

