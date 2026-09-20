# 여기말GO 백엔드

FastAPI 기반 백엔드 서버

## 요구 사항

* Python 3.11+
* Supabase 프로젝트

  * PostgreSQL
  * Supabase Auth

## 로컬 실행

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
```

프로젝트 실행에 필요한 환경 변수는 `.env.example`을 참고하여 `.env`에 설정합니다.

## DB 마이그레이션

```bash
cd backend
source .venv/bin/activate

alembic upgrade head
```

Supabase Dashboard SQL Editor에서 `supabase/rls.sql`도 실행해 RLS 정책을 적용하세요.

## 서버 실행

```bash
cd backend
source .venv/bin/activate

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

요청 횟수 제한(rate limit)은 IP 기준이다(전역 120/분, 회원가입 5/분, 장소 검색 30/분).
프록시/로드밸런서 뒤에 배포하면 모든 요청이 프록시 IP 로 보여 사용자가 한도를 공유하므로,
`--proxy-headers --forwarded-allow-ips=<프록시 IP>` 옵션으로 실행해야 한다.
로컬에서 끄려면 `.env` 에 `RATE_LIMIT_ENABLED=false` 를 둔다.

서버 실행 후 다음 주소에서 상태 및 API 문서를 확인할 수 있습니다.

* Health Check: `http://localhost:8000/health`
* Swagger UI: `http://localhost:8000/docs`

## 인증

* 회원가입: `POST /api/auth/signup`
* OAuth 프로필 보정: `POST /api/auth/ensure-profile` (카카오 등 소셜 첫 로그인)
* 로그인 / 로그아웃 / 토큰 갱신: 프론트엔드에서 Supabase Auth 사용
* 카카오 로그인 키는 백엔드 env가 아니라 Supabase Dashboard > Authentication > Providers > Kakao
* 보호 API는 `Authorization: Bearer <access_token>` 필요

## 주요 API

* `GET /api/home` — 홈 요약 (진행 중/최근 일정)
* `GET|PATCH /api/users/me` — 내 프로필
* `GET|POST /api/schedules`, `GET|PATCH|DELETE /api/schedules/{id}` — 일정·장소 CRUD

## Health Check

```http
GET /health
```

정상 응답:

```json
{
  "status": "ok"
}
```

## 에러 응답

API 에러는 다음 형식으로 반환됩니다.

```json
{
  "code": "AUTH_TOKEN_INVALID",
  "message": "인증 토큰이 유효하지 않습니다."
}
```

## 테스트

```bash
cd backend
source .venv/bin/activate
pytest
```
