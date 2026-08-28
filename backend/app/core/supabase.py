"""Supabase Python 클라이언트를 생성하는 공통 모듈이다.

publishable key 는 signup·JWT 검증 등 Auth API 호출에 쓰고,
secret key 는 서버 전용 관리자 작업용으로만 보관한다. 현재는 미사용이다.
"""
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_anon_client() -> Client:
    """읽기 전용에 가까운 공용 Auth 클라이언트를 캐시해 재사용한다."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY)


@lru_cache
def get_service_client() -> Client:
    """RLS 우회가 가능한 관리자 클라이언트를 준비한다. 현재는 미사용이다."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)


def new_anon_client() -> Client:
    """요청마다 새 Auth 클라이언트를 만들어 세션 상태 공유를 막는다."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY)
