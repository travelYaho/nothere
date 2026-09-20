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
    # 키 발급 전까지는 빈 문자열로 두고, TourAPI 클라이언트가 그 상태를
    # EXTERNAL_API_UNAVAILABLE(503) 로 방어적으로 처리한다. Supabase 키와
    # 달리 필수값 검증을 걸지 않아 키 없이도 서버는 정상 기동한다.
    TOUR_API_KEY: str = ""
    # 장소 직접 추가 시 주소 -> 위경도 지오코딩에 쓴다. TourAPI 와 마찬가지로
    # 없어도 서버는 뜨고, 실제 호출 시점에 EXTERNAL_API_UNAVAILABLE 로 방어한다.
    KAKAO_REST_API_KEY: str = ""
    # 카카오 연결 해제 웹훅 인증(Authorization: KakaoAK ...). 없으면 웹훅은 401.
    KAKAO_ADMIN_KEY: str = ""
    ROUTE_CACHE_TTL_HOURS: int = 24
    FRONTEND_PUBLIC_ORIGIN: str = "http://localhost:5173"
    CONCENTRATION_API_KEY: str = ""
    TOUR_API_KEY: str = ""

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
