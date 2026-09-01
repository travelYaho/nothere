# Frontend

Vite + React + TypeScript 스켈레톤입니다. Supabase Auth로 로그인하고, Bearer 토큰으로 백엔드 `/api/home`, `/api/users/me`를 호출합니다.

## 실행

```bash
cd frontend
cp .env.example .env
# VITE_SUPABASE_URL, VITE_SUPABASE_PUBLISHABLE_KEY 설정

npm install
npm run dev
```

- 개발 서버: `http://localhost:5173`
- API는 `VITE_API_BASE_URL`(기본 `http://localhost:8000`)로 요청합니다.
- 회원가입은 백엔드 `POST /api/auth/signup`, 로그인은 Supabase Auth를 사용합니다.
