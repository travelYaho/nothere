-- 여기말GO RLS policies
-- Supabase Dashboard SQL Editor에서 실행합니다.
-- FastAPI는 DATABASE_URL(postgres 롤)로 접속하므로 RLS를 우회할 수 있습니다.
-- 서버 레이어에서 user_id = 현재 로그인 사용자 검증을 반드시 유지하세요.

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.schedules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_select_own" ON public.profiles;
DROP POLICY IF EXISTS "profiles_insert_own" ON public.profiles;
DROP POLICY IF EXISTS "profiles_update_own" ON public.profiles;

CREATE POLICY "profiles_select_own"
ON public.profiles
FOR SELECT
USING (auth.uid() = id);

CREATE POLICY "profiles_insert_own"
ON public.profiles
FOR INSERT
WITH CHECK (auth.uid() = id);

CREATE POLICY "profiles_update_own"
ON public.profiles
FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "schedules_select_own" ON public.schedules;
DROP POLICY IF EXISTS "schedules_insert_own" ON public.schedules;
DROP POLICY IF EXISTS "schedules_update_own" ON public.schedules;
DROP POLICY IF EXISTS "schedules_delete_own" ON public.schedules;

CREATE POLICY "schedules_select_own"
ON public.schedules
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "schedules_insert_own"
ON public.schedules
FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "schedules_update_own"
ON public.schedules
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "schedules_delete_own"
ON public.schedules
FOR DELETE
USING (auth.uid() = user_id);
