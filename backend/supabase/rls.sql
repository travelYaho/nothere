-- 여기말GO RLS policies (unified schema)
-- schema.sql 또는 alembic upgrade 이후 실행.
-- FastAPI DATABASE_URL(postgres 롤)은 RLS를 우회할 수 있음 → 앱 레이어 user 검증 유지.

-- =============================================================================
-- profile: auth.uid() = id
-- =============================================================================
ALTER TABLE public.profile ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profile_select_own" ON public.profile;
DROP POLICY IF EXISTS "profile_insert_own" ON public.profile;
DROP POLICY IF EXISTS "profile_update_own" ON public.profile;

CREATE POLICY "profile_select_own" ON public.profile
  FOR SELECT USING (auth.uid() = id);
CREATE POLICY "profile_insert_own" ON public.profile
  FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "profile_update_own" ON public.profile
  FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- =============================================================================
-- trip: auth.uid() = user_id
-- =============================================================================
ALTER TABLE public.trip ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "trip_select_own" ON public.trip;
DROP POLICY IF EXISTS "trip_insert_own" ON public.trip;
DROP POLICY IF EXISTS "trip_update_own" ON public.trip;
DROP POLICY IF EXISTS "trip_delete_own" ON public.trip;

CREATE POLICY "trip_select_own" ON public.trip
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "trip_insert_own" ON public.trip
  FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "trip_update_own" ON public.trip
  FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "trip_delete_own" ON public.trip
  FOR DELETE USING (auth.uid() = user_id);

-- =============================================================================
-- trip_place → trip.user_id
-- =============================================================================
ALTER TABLE public.trip_place ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "trip_place_select_own" ON public.trip_place;
DROP POLICY IF EXISTS "trip_place_insert_own" ON public.trip_place;
DROP POLICY IF EXISTS "trip_place_update_own" ON public.trip_place;
DROP POLICY IF EXISTS "trip_place_delete_own" ON public.trip_place;

CREATE POLICY "trip_place_select_own" ON public.trip_place
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  );
CREATE POLICY "trip_place_insert_own" ON public.trip_place
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  );
CREATE POLICY "trip_place_update_own" ON public.trip_place
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  ) WITH CHECK (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  );
CREATE POLICY "trip_place_delete_own" ON public.trip_place
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  );

-- =============================================================================
-- trip_place_purpose → trip_place → trip.user_id
-- =============================================================================
ALTER TABLE public.trip_place_purpose ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "trip_place_purpose_all_own" ON public.trip_place_purpose;

CREATE POLICY "trip_place_purpose_all_own" ON public.trip_place_purpose
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.trip_place tp
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE tp.id = trip_place_id AND t.user_id = auth.uid()
    )
  ) WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.trip_place tp
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE tp.id = trip_place_id AND t.user_id = auth.uid()
    )
  );

-- =============================================================================
-- trip_preferred_experience → trip.user_id
-- =============================================================================
ALTER TABLE public.trip_preferred_experience ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "trip_preferred_experience_all_own" ON public.trip_preferred_experience;

CREATE POLICY "trip_preferred_experience_all_own" ON public.trip_preferred_experience
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  ) WITH CHECK (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  );

-- =============================================================================
-- trip_place_analysis → trip_place → trip.user_id
-- =============================================================================
ALTER TABLE public.trip_place_analysis ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "trip_place_analysis_all_own" ON public.trip_place_analysis;

CREATE POLICY "trip_place_analysis_all_own" ON public.trip_place_analysis
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.trip_place tp
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE tp.id = trip_place_id AND t.user_id = auth.uid()
    )
  ) WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.trip_place tp
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE tp.id = trip_place_id AND t.user_id = auth.uid()
    )
  );

-- =============================================================================
-- recommendation_request → trip_place → trip.user_id
-- =============================================================================
ALTER TABLE public.recommendation_request ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "recommendation_request_all_own" ON public.recommendation_request;

CREATE POLICY "recommendation_request_all_own" ON public.recommendation_request
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.trip_place tp
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE tp.id = trip_place_id AND t.user_id = auth.uid()
    )
  ) WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.trip_place tp
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE tp.id = trip_place_id AND t.user_id = auth.uid()
    )
  );

-- =============================================================================
-- recommendation_candidate → request → trip_place → trip.user_id
-- =============================================================================
ALTER TABLE public.recommendation_candidate ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "recommendation_candidate_all_own" ON public.recommendation_candidate;

CREATE POLICY "recommendation_candidate_all_own" ON public.recommendation_candidate
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.recommendation_request rr
      JOIN public.trip_place tp ON tp.id = rr.trip_place_id
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE rr.id = request_id AND t.user_id = auth.uid()
    )
  ) WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.recommendation_request rr
      JOIN public.trip_place tp ON tp.id = rr.trip_place_id
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE rr.id = request_id AND t.user_id = auth.uid()
    )
  );

-- =============================================================================
-- ranking / route / reason → candidate → request → trip_place → trip.user_id
-- =============================================================================
ALTER TABLE public.recommendation_ranking ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recommendation_route ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.recommendation_reason ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "recommendation_ranking_all_own" ON public.recommendation_ranking;
DROP POLICY IF EXISTS "recommendation_route_all_own" ON public.recommendation_route;
DROP POLICY IF EXISTS "recommendation_reason_all_own" ON public.recommendation_reason;

CREATE POLICY "recommendation_ranking_all_own" ON public.recommendation_ranking
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.recommendation_candidate rc
      JOIN public.recommendation_request rr ON rr.id = rc.request_id
      JOIN public.trip_place tp ON tp.id = rr.trip_place_id
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE rc.id = candidate_id AND t.user_id = auth.uid()
    )
  ) WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.recommendation_candidate rc
      JOIN public.recommendation_request rr ON rr.id = rc.request_id
      JOIN public.trip_place tp ON tp.id = rr.trip_place_id
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE rc.id = candidate_id AND t.user_id = auth.uid()
    )
  );

CREATE POLICY "recommendation_route_all_own" ON public.recommendation_route
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.recommendation_candidate rc
      JOIN public.recommendation_request rr ON rr.id = rc.request_id
      JOIN public.trip_place tp ON tp.id = rr.trip_place_id
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE rc.id = candidate_id AND t.user_id = auth.uid()
    )
  ) WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.recommendation_candidate rc
      JOIN public.recommendation_request rr ON rr.id = rc.request_id
      JOIN public.trip_place tp ON tp.id = rr.trip_place_id
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE rc.id = candidate_id AND t.user_id = auth.uid()
    )
  );

CREATE POLICY "recommendation_reason_all_own" ON public.recommendation_reason
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.recommendation_candidate rc
      JOIN public.recommendation_request rr ON rr.id = rc.request_id
      JOIN public.trip_place tp ON tp.id = rr.trip_place_id
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE rc.id = candidate_id AND t.user_id = auth.uid()
    )
  ) WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.recommendation_candidate rc
      JOIN public.recommendation_request rr ON rr.id = rc.request_id
      JOIN public.trip_place tp ON tp.id = rr.trip_place_id
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE rc.id = candidate_id AND t.user_id = auth.uid()
    )
  );

-- =============================================================================
-- replacement → trip_place → trip.user_id
-- =============================================================================
ALTER TABLE public.replacement ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "replacement_all_own" ON public.replacement;

CREATE POLICY "replacement_all_own" ON public.replacement
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM public.trip_place tp
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE tp.id = trip_place_id AND t.user_id = auth.uid()
    )
  ) WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.trip_place tp
      JOIN public.trip t ON t.id = tp.trip_id
      WHERE tp.id = trip_place_id AND t.user_id = auth.uid()
    )
  );

-- =============================================================================
-- recommendation_interaction → trip.user_id
-- =============================================================================
ALTER TABLE public.recommendation_interaction ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "recommendation_interaction_all_own" ON public.recommendation_interaction;

CREATE POLICY "recommendation_interaction_all_own" ON public.recommendation_interaction
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  ) WITH CHECK (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  );

-- =============================================================================
-- share_link → trip.user_id (+ token 공개 읽기)
-- =============================================================================
ALTER TABLE public.share_link ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "share_link_all_own" ON public.share_link;
DROP POLICY IF EXISTS "share_link_select_active_token" ON public.share_link;

CREATE POLICY "share_link_all_own" ON public.share_link
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  ) WITH CHECK (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  );

CREATE POLICY "share_link_select_active_token" ON public.share_link
  FOR SELECT USING (
    revoked_at IS NULL
    AND (expires_at IS NULL OR expires_at > now())
    AND visibility = 'link'
  );

-- =============================================================================
-- guide_entry → trip.user_id (+ is_public 읽기)
-- =============================================================================
ALTER TABLE public.guide_entry ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "guide_entry_all_own" ON public.guide_entry;
DROP POLICY IF EXISTS "guide_entry_select_public" ON public.guide_entry;

CREATE POLICY "guide_entry_all_own" ON public.guide_entry
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  ) WITH CHECK (
    EXISTS (SELECT 1 FROM public.trip t WHERE t.id = trip_id AND t.user_id = auth.uid())
  );

CREATE POLICY "guide_entry_select_public" ON public.guide_entry
  FOR SELECT USING (is_public = TRUE);

-- =============================================================================
-- user_long_term_preference: SELECT 본인 / CUD는 service role만
-- =============================================================================
ALTER TABLE public.user_long_term_preference ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_long_term_preference_select_own" ON public.user_long_term_preference;

CREATE POLICY "user_long_term_preference_select_own" ON public.user_long_term_preference
  FOR SELECT USING (auth.uid() = user_id);
-- INSERT/UPDATE/DELETE 정책 없음 → authenticated 클라이언트는 CUD 불가 (service role만)

-- =============================================================================
-- 서버 전용 (RLS enable, authenticated 정책 없음 = deny-by-default)
-- =============================================================================
ALTER TABLE public.api_fetch_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.place ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.region ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experience_tag ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.concentration_spot ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.place_concentration_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.route_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.place_experience_tag ENABLE ROW LEVEL SECURITY;
