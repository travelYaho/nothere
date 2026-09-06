"""환경변수를 읽어 애플리케이션 공통 설정으로 노출한다.

Supabase Auth 는 SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY 를 사용하고,
SQLAlchemy 는 DATABASE_URL 을 사용해 Supabase Postgres 에 직접 연결한다.
"""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """backend/.env 값을 검증하고 코드에서 재사용하기 쉽게 가공한다."""
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SUPABASE_URL: str
    SUPABASE_PUBLISHABLE_KEY: str
    SUPABASE_SECRET_KEY: str
    DATABASE_URL: str
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    KAKAO_REST_API_KEY: str = ""
    ROUTE_CACHE_TTL_HOURS: int = 24
    FRONTEND_PUBLIC_ORIGIN: str = "http://localhost:5173"

    @field_validator(
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_SECRET_KEY",
        "DATABASE_URL",
    )
    @classmethod
    def not_empty(cls, value: str) -> str:
        """필수 키가 비어 있으면 서버 시작 단계에서 바로 실패시킨다."""
        if not value.strip():
            raise ValueError("환경변수가 비어 있습니다. backend/.env 를 확인하세요.")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """콤마 구분 CORS_ORIGINS 문자열을 리스트로 변환한다."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """SQLAlchemy 드라이버 형식에 맞게 postgres URL 접두사를 정규화한다."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()
