"""Supabase Python 클라이언트를 생성하는 공통 모듈이다.

publishable key 는 signup·JWT 검증 등 Auth API 호출에 쓰고,
secret key 는 프로필 생성 실패 시 Auth 유저 롤백 등 서버 전용 관리 작업에 쓴다.
"""
from functools import lru_cache
from uuid import UUID

from supabase import Client, create_client

from app.core.config import settings


@lru_cache
def get_anon_client() -> Client:
    """읽기 전용에 가까운 공용 Auth 클라이언트를 캐시해 재사용한다."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY)


@lru_cache
def get_service_client() -> Client:
    """RLS 우회가 가능한 관리자 클라이언트를 준비한다."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)


def new_anon_client() -> Client:
    """요청마다 새 Auth 클라이언트를 만들어 세션 상태 공유를 막는다."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY)


def delete_auth_user(user_id: UUID) -> None:
    """service role 로 Auth 사용자를 삭제한다. signup 보상 트랜잭션용."""
    get_service_client().auth.admin.delete_user(str(user_id))
