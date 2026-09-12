-- 여기말GO unified schema (Part0~3)
-- Alembic Source of Truth 와 동일 스냅샷. SQL Editor 초기 세팅용.
-- schema.sql 실행 후 alembic upgrade head 를 다시 실행하지 마세요 (CREATE 충돌).
-- 방법 A: schema.sql → rls.sql → alembic stamp head
-- 방법 B: alembic upgrade head → rls.sql

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 공통
-- =============================================================================

CREATE TABLE public.profile (
  id UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  nickname VARCHAR(50) NOT NULL,
  profile_image_url TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER profile_set_updated_at
BEFORE UPDATE ON public.profile
FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();

CREATE TABLE public.api_fetch_log (
  id BIGSERIAL PRIMARY KEY,
  provider VARCHAR(50) NOT NULL,
  endpoint VARCHAR(500) NOT NULL,
  status_code INTEGER NULL,
  result_code VARCHAR(50) NULL,
  success BOOLEAN NOT NULL,
  duration_ms INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- Part1: 여행/장소/취향
-- =============================================================================

CREATE TABLE public.region (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  is_supported BOOLEAN NOT NULL DEFAULT FALSE,
  area_cd VARCHAR(20) NULL,
  signgu_cd VARCHAR(20) NULL
);

CREATE TABLE public.experience_tag (
  id SMALLSERIAL PRIMARY KEY,
  code VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE public.place (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type VARCHAR(50) NULL,
  tour_content_id VARCHAR(50) NULL,
  region_id BIGINT NULL REFERENCES public.region (id),
  name VARCHAR(200) NOT NULL,
  location GEOGRAPHY(POINT, 4326) NULL,
  is_recommendable BOOLEAN NOT NULL DEFAULT TRUE,
  area_cd VARCHAR(20) NULL,
  signgu_cd VARCHAR(20) NULL,
  UNIQUE (source_type, tour_content_id)
);

CREATE INDEX ix_place_region_id ON public.place (region_id);
CREATE INDEX ix_place_tour_content_id ON public.place (tour_content_id);

CREATE TABLE public.trip (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.profile (id) ON DELETE CASCADE,
  region_id BIGINT NULL REFERENCES public.region (id),
  title VARCHAR(200) NOT NULL,
  travel_date DATE NULL,
  companion_type VARCHAR(50) NULL,
  transport_mode VARCHAR(50) NULL,
  extra_time_limit_minutes SMALLINT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  current_step SMALLINT NULL,
  needs_reanalysis BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  confirmed_at TIMESTAMPTZ NULL
);

CREATE INDEX ix_trip_user_id ON public.trip (user_id);
CREATE INDEX ix_trip_region_id ON public.trip (region_id);

CREATE TABLE public.trip_place (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id UUID NOT NULL REFERENCES public.trip (id) ON DELETE CASCADE,
  place_id UUID NOT NULL REFERENCES public.place (id),
  initial_place_id UUID NULL REFERENCES public.place (id),
  position SMALLINT NOT NULL,
  visit_time TIME NULL,
  stay_minutes SMALLINT NULL,
  is_fixed BOOLEAN NOT NULL DEFAULT FALSE,
  resolution_status VARCHAR(20) NOT NULL DEFAULT 'pending'
);

CREATE INDEX ix_trip_place_trip_id ON public.trip_place (trip_id);
CREATE INDEX ix_trip_place_place_id ON public.trip_place (place_id);

CREATE TABLE public.trip_place_purpose (
  trip_place_id UUID NOT NULL REFERENCES public.trip_place (id) ON DELETE CASCADE,
  purpose_tag_id SMALLINT NOT NULL REFERENCES public.experience_tag (id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (trip_place_id, purpose_tag_id)
);

CREATE TABLE public.trip_preferred_experience (
  trip_id UUID NOT NULL REFERENCES public.trip (id) ON DELETE CASCADE,
  experience_tag_id SMALLINT NOT NULL REFERENCES public.experience_tag (id),
  weight NUMERIC(5, 4) NOT NULL,
  PRIMARY KEY (trip_id, experience_tag_id)
);

CREATE TABLE public.place_experience_tag (
  place_id UUID NOT NULL REFERENCES public.place (id) ON DELETE CASCADE,
  experience_tag_id SMALLINT NOT NULL REFERENCES public.experience_tag (id),
  weight NUMERIC(5, 4) NOT NULL,
  source VARCHAR(50) NULL,
  PRIMARY KEY (place_id, experience_tag_id)
);

CREATE TABLE public.user_long_term_preference (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
  experience_tag_id SMALLINT NOT NULL REFERENCES public.experience_tag (id),
  score NUMERIC(8, 4) NOT NULL DEFAULT 0,
  trip_count SMALLINT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, experience_tag_id)
);

-- =============================================================================
-- Part2: 집중도 분석 / 후보 / 점수·순위
-- =============================================================================

CREATE TABLE public.concentration_spot (
  id BIGSERIAL PRIMARY KEY,
  area_cd VARCHAR(20) NOT NULL,
  signgu_cd VARCHAR(20) NOT NULL,
  tourist_name VARCHAR(200) NOT NULL,
  normalized_name VARCHAR(200) NOT NULL,
  UNIQUE (area_cd, signgu_cd, tourist_name)
);

CREATE TABLE public.place_concentration_mapping (
  id BIGSERIAL PRIMARY KEY,
  place_id UUID NOT NULL REFERENCES public.place (id) ON DELETE CASCADE,
  concentration_spot_id BIGINT NOT NULL REFERENCES public.concentration_spot (id) ON DELETE CASCADE,
  match_method VARCHAR(20) NOT NULL,
  confidence NUMERIC(5, 4) NULL,
  status VARCHAR(20) NOT NULL,
  reviewed_by UUID NULL REFERENCES auth.users (id),
  reviewed_at TIMESTAMPTZ NULL
);

CREATE INDEX ix_place_concentration_mapping_place_id
  ON public.place_concentration_mapping (place_id);

CREATE TABLE public.trip_place_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_place_id UUID NOT NULL REFERENCES public.trip_place (id) ON DELETE CASCADE,
  analysis_status VARCHAR(20) NOT NULL,
  level VARCHAR(20) NULL,
  unknown_reason VARCHAR(30) NULL,
  rule_version VARCHAR(20) NULL,
  analyzed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_trip_place_analysis_trip_place_id
  ON public.trip_place_analysis (trip_place_id);

CREATE TABLE public.recommendation_request (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_place_id UUID NOT NULL REFERENCES public.trip_place (id) ON DELETE CASCADE,
  search_mode VARCHAR(20) NOT NULL DEFAULT 'default',
  status VARCHAR(20) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ NULL
);

CREATE INDEX ix_recommendation_request_trip_place_id
  ON public.recommendation_request (trip_place_id);

CREATE TABLE public.recommendation_candidate (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id UUID NOT NULL REFERENCES public.recommendation_request (id) ON DELETE CASCADE,
  candidate_place_id UUID NOT NULL REFERENCES public.place (id),
  experience_score NUMERIC(5, 4) NOT NULL,
  congestion_level VARCHAR(20) NOT NULL,
  feasibility_status VARCHAR(20) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_recommendation_candidate_request_id
  ON public.recommendation_candidate (request_id);

-- Part2: 최종 점수/순위 (candidate 1:1)
CREATE TABLE public.recommendation_ranking (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL UNIQUE REFERENCES public.recommendation_candidate (id) ON DELETE CASCADE,
  route_score NUMERIC(5, 4) NULL,
  congestion_score NUMERIC(5, 4) NULL,
  operation_score NUMERIC(5, 4) NULL,
  total_score NUMERIC(5, 4) NULL,
  rank SMALLINT NULL,
  scored_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- Part3: 경로/이유 / 교체 / 로그 / 공유·가이드
-- =============================================================================

-- candidate 일정 문맥 경로 평가 (trip/candidate 종속). route_cache 와 역할 분리.
CREATE TABLE public.recommendation_route (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL UNIQUE REFERENCES public.recommendation_candidate (id) ON DELETE CASCADE,
  distance_prev_m INTEGER NULL,
  distance_next_m INTEGER NULL,
  extra_minutes INTEGER NULL,
  route_source VARCHAR(20) NULL,
  is_route_estimated BOOLEAN NOT NULL DEFAULT FALSE,
  calculated_at TIMESTAMPTZ NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 추천/비추천 이유·노출 여부. 실제 선택은 replacement 로 판단 (is_selected 없음).
CREATE TABLE public.recommendation_reason (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL UNIQUE REFERENCES public.recommendation_candidate (id) ON DELETE CASCADE,
  recommend_reason TEXT NULL,
  not_recommend_reason TEXT NULL,
  reason_source_snapshot JSONB NULL,
  is_eligible BOOLEAN NOT NULL DEFAULT TRUE,
  exclusion_reason VARCHAR(50) NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER recommendation_reason_set_updated_at
BEFORE UPDATE ON public.recommendation_reason
FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();

-- 장소 A→B 지도 API 캐시 (trip/candidate 무관)
CREATE TABLE public.route_cache (
  id BIGSERIAL PRIMARY KEY,
  origin_place_id UUID NOT NULL REFERENCES public.place (id),
  destination_place_id UUID NOT NULL REFERENCES public.place (id),
  transport_mode VARCHAR(20) NOT NULL,
  distance_m INTEGER NOT NULL,
  duration_seconds INTEGER NOT NULL,
  provider VARCHAR(30) NOT NULL,
  is_estimated BOOLEAN NOT NULL DEFAULT FALSE,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  UNIQUE (origin_place_id, destination_place_id, transport_mode, provider)
);

CREATE TABLE public.replacement (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_place_id UUID NOT NULL REFERENCES public.trip_place (id) ON DELETE CASCADE,
  from_place_id UUID NOT NULL REFERENCES public.place (id),
  to_place_id UUID NOT NULL REFERENCES public.place (id),
  ranking_id UUID NULL REFERENCES public.recommendation_ranking (id) ON DELETE SET NULL,
  reason_snapshot TEXT NULL,
  extra_minutes INTEGER NULL,
  before_level VARCHAR(20) NULL,
  after_level VARCHAR(20) NULL,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reverted_at TIMESTAMPTZ NULL
);

CREATE INDEX ix_replacement_trip_place_id ON public.replacement (trip_place_id);

CREATE TABLE public.recommendation_interaction (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users (id),
  trip_id UUID NOT NULL REFERENCES public.trip (id) ON DELETE CASCADE,
  trip_place_id UUID NOT NULL REFERENCES public.trip_place (id) ON DELETE CASCADE,
  ranking_id UUID NULL REFERENCES public.recommendation_ranking (id) ON DELETE SET NULL,
  event_type VARCHAR(40) NOT NULL,
  position SMALLINT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_recommendation_interaction_trip_id
  ON public.recommendation_interaction (trip_id);

CREATE TABLE public.share_link (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id UUID NOT NULL REFERENCES public.trip (id) ON DELETE CASCADE,
  token VARCHAR(64) NOT NULL UNIQUE,
  visibility VARCHAR(20) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NULL,
  revoked_at TIMESTAMPTZ NULL
);

CREATE INDEX ix_share_link_trip_id ON public.share_link (trip_id);

CREATE TABLE public.guide_entry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id UUID NOT NULL REFERENCES public.trip (id) ON DELETE CASCADE,
  trip_place_id UUID NULL REFERENCES public.trip_place (id) ON DELETE SET NULL,
  entry_date DATE NULL,
  image_url TEXT NULL,
  image_key TEXT NULL,
  image_original_name VARCHAR(255) NULL,
  image_content_type VARCHAR(100) NULL,
  content TEXT NULL,
  is_public BOOLEAN NOT NULL DEFAULT FALSE,
  display_order SMALLINT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_guide_entry_trip_id ON public.guide_entry (trip_id);

CREATE TRIGGER guide_entry_set_updated_at
BEFORE UPDATE ON public.guide_entry
FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();
