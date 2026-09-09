-- 여기말GO RLS policies
-- Supabase Dashboard SQL Editor에서 실행합니다.
-- FastAPI는 DATABASE_URL(postgres 롤)로 접속하므로 RLS를 우회할 수 있습니다.
-- 서버 레이어에서 user_id = 현재 로그인 사용자 검증을 반드시 유지하세요.

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trip_places ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trip_preferred_experiences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trip_place_purposes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_long_term_preferences ENABLE ROW LEVEL SECURITY;

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

-- trips: schedules_* 정책을 동일한 소유자 규칙으로 대체한다.
DROP POLICY IF EXISTS "trips_select_own" ON public.trips;
DROP POLICY IF EXISTS "trips_insert_own" ON public.trips;
DROP POLICY IF EXISTS "trips_update_own" ON public.trips;
DROP POLICY IF EXISTS "trips_delete_own" ON public.trips;

CREATE POLICY "trips_select_own"
ON public.trips
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "trips_insert_own"
ON public.trips
FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "trips_update_own"
ON public.trips
FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "trips_delete_own"
ON public.trips
FOR DELETE
USING (auth.uid() = user_id);

-- trip_places / trip_preferred_experiences / trip_place_purposes 는 자체 user_id가
-- 없으므로 trips.user_id 를 조인해 소유권을 확인한다.
DROP POLICY IF EXISTS "trip_places_owner_all" ON public.trip_places;

CREATE POLICY "trip_places_owner_all"
ON public.trip_places
FOR ALL
USING (EXISTS (
    SELECT 1 FROM public.trips
    WHERE trips.id = trip_places.trip_id AND trips.user_id = auth.uid()
))
WITH CHECK (EXISTS (
    SELECT 1 FROM public.trips
    WHERE trips.id = trip_places.trip_id AND trips.user_id = auth.uid()
));

DROP POLICY IF EXISTS "trip_preferred_experiences_owner_all" ON public.trip_preferred_experiences;

CREATE POLICY "trip_preferred_experiences_owner_all"
ON public.trip_preferred_experiences
FOR ALL
USING (EXISTS (
    SELECT 1 FROM public.trips
    WHERE trips.id = trip_preferred_experiences.trip_id AND trips.user_id = auth.uid()
))
WITH CHECK (EXISTS (
    SELECT 1 FROM public.trips
    WHERE trips.id = trip_preferred_experiences.trip_id AND trips.user_id = auth.uid()
));

DROP POLICY IF EXISTS "trip_place_purposes_owner_all" ON public.trip_place_purposes;

CREATE POLICY "trip_place_purposes_owner_all"
ON public.trip_place_purposes
FOR ALL
USING (EXISTS (
    SELECT 1 FROM public.trip_places
    JOIN public.trips ON trips.id = trip_places.trip_id
    WHERE trip_places.id = trip_place_purposes.trip_place_id AND trips.user_id = auth.uid()
))
WITH CHECK (EXISTS (
    SELECT 1 FROM public.trip_places
    JOIN public.trips ON trips.id = trip_places.trip_id
    WHERE trip_places.id = trip_place_purposes.trip_place_id AND trips.user_id = auth.uid()
));

-- user_long_term_preferences 는 자체 user_id 컬럼을 가진다(로드맵 기능).
DROP POLICY IF EXISTS "user_long_term_preferences_owner_all" ON public.user_long_term_preferences;

CREATE POLICY "user_long_term_preferences_owner_all"
ON public.user_long_term_preferences
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- regions / experience_tags / places / place_experience_tags 는 사용자 소유가 아닌
-- 참조(카탈로그) 데이터라 RLS를 걸지 않는다. FastAPI 가 DATABASE_URL(postgres 롤)로
-- 접속해 우회하는 것과 별개로, Supabase 클라이언트가 직접 조회해도 안전한 공개 데이터다.

-- 가이드북 공개 갤러리·좋아요: share_link/guide_entry 는 소유자만 관리하되,
-- visibility='public' 인 링크와 그에 딸린 공개 그림일기는 누구나 조회할 수 있어야
-- 탐색 갤러리가 Supabase 클라이언트로 직접 조회되는 경우에도 동작한다.
ALTER TABLE public.share_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guide_entry ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guide_like ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "share_link_select_public_or_owner" ON public.share_link;
DROP POLICY IF EXISTS "share_link_owner_write" ON public.share_link;

CREATE POLICY "share_link_select_public_or_owner"
ON public.share_link
FOR SELECT
USING (
    visibility = 'public'
    OR EXISTS (
        SELECT 1 FROM public.trips
        WHERE trips.id = share_link.trip_id AND trips.user_id = auth.uid()
    )
);

CREATE POLICY "share_link_owner_write"
ON public.share_link
FOR ALL
USING (EXISTS (
    SELECT 1 FROM public.trips
    WHERE trips.id = share_link.trip_id AND trips.user_id = auth.uid()
))
WITH CHECK (EXISTS (
    SELECT 1 FROM public.trips
    WHERE trips.id = share_link.trip_id AND trips.user_id = auth.uid()
));

DROP POLICY IF EXISTS "guide_entry_select_public_or_owner" ON public.guide_entry;
DROP POLICY IF EXISTS "guide_entry_owner_write" ON public.guide_entry;

CREATE POLICY "guide_entry_select_public_or_owner"
ON public.guide_entry
FOR SELECT
USING (
    (is_public AND EXISTS (
        SELECT 1 FROM public.share_link
        WHERE share_link.trip_id = guide_entry.trip_id AND share_link.visibility = 'public'
    ))
    OR EXISTS (
        SELECT 1 FROM public.trips
        WHERE trips.id = guide_entry.trip_id AND trips.user_id = auth.uid()
    )
);

CREATE POLICY "guide_entry_owner_write"
ON public.guide_entry
FOR ALL
USING (EXISTS (
    SELECT 1 FROM public.trips
    WHERE trips.id = guide_entry.trip_id AND trips.user_id = auth.uid()
))
WITH CHECK (EXISTS (
    SELECT 1 FROM public.trips
    WHERE trips.id = guide_entry.trip_id AND trips.user_id = auth.uid()
));

-- guide_like: 비로그인 좋아요는 지원하지 않는다(단순화) — 본인 좋아요만 보고 관리한다.
DROP POLICY IF EXISTS "guide_like_owner_all" ON public.guide_like;

CREATE POLICY "guide_like_owner_all"
ON public.guide_like
FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
