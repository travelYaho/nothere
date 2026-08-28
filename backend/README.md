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

## 서버 실행

```bash
cd backend
source .venv/bin/activate

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

서버 실행 후 다음 주소에서 상태 및 API 문서를 확인할 수 있습니다.

* Health Check: `http://localhost:8000/health`
* Swagger UI: `http://localhost:8000/docs`

## 인증

* 회원가입: `POST /api/auth/signup`
* 로그인 / 로그아웃 / 토큰 갱신: 프론트엔드에서 Supabase Auth 사용
* 일부 API는 인증 후 사용할 수 있습니다.


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

```

## 에러 응답

API 에러는 다음 형식으로 반환됩니다.

```json
{
  "code": "AUTH_TOKEN_INVALID",
  "message": "인증 토큰이 유효하지 않습니다."
}
```
