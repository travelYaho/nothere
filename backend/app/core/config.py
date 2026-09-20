"""환경변수를 읽어 애플리케이션 공통 설정으로 노출한다.

Supabase Auth 는 SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY 를 사용하고,
SQLAlchemy 는 DATABASE_URL 을 사용해 Supabase Postgres 에 직접 연결한다.
"""
from pathlib import Path

from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


def expand_cors_origins(raw: str) -> list[str]:
    """CORS_ORIGINS 값을 리스트로 만들고 localhost↔127.0.0.1 별칭을 보탠다."""
    seen: list[str] = []
    for part in raw.split(","):
        origin = part.strip().rstrip("/")
        if not origin:
            continue
        for candidate in _localhost_aliases(origin):
            if candidate not in seen:
                seen.append(candidate)
    return seen


def _localhost_aliases(origin: str) -> list[str]:
    parsed = urlparse(origin)
    host = parsed.hostname or ""
    aliases = [origin]
    if host == "localhost":
        netloc = parsed.netloc.replace("localhost", "127.0.0.1", 1)
        aliases.append(parsed._replace(netloc=netloc).geturl())
    elif host == "127.0.0.1":
        netloc = parsed.netloc.replace("127.0.0.1", "localhost", 1)
        aliases.append(parsed._replace(netloc=netloc).geturl())
    return aliases


def cors_origin_regex(origins: list[str]) -> str | None:
    """CORS_ORIGINS 에 있는 포트로 사설망·루프백 Origin 을 허용하는 정규식."""
    ports: set[int] = set()
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.port:
            ports.add(parsed.port)
        elif parsed.scheme == "https":
            ports.add(443)
        elif parsed.scheme == "http":
            ports.add(80)
    if not ports:
        return None
    port_alt = "|".join(str(port) for port in sorted(ports))
    return (
        r"https?://("
        r"localhost|127\.0\.0\.1|\[::1\]|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
        rf"):({port_alt})$"
    )


class Settings(BaseSettings):
    """backend/.env 값을 검증하고 코드에서 재사용하기 쉽게 가공한다."""
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
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
    # 요청 횟수 제한(IP 기준) 스위치. 테스트에서만 끈다.
    RATE_LIMIT_ENABLED: bool = True
    FRONTEND_PUBLIC_ORIGIN: str = "http://localhost:5173"
    CONCENTRATION_API_KEY: str = ""
    # 관광사진(PhotoGalleryService1). KorService2 키와 활용신청이 다르다.
    # .env 의 PHOTO_GALLERY_API_KEY 도 그대로 읽는다.
    TOUR_GALLERY_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("TOUR_GALLERY_KEY", "PHOTO_GALLERY_API_KEY"),
    )

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
        return expand_cors_origins(self.CORS_ORIGINS)

    @property
    def cors_origin_regex(self) -> str | None:
        """Vite --host 0.0.0.0 의 LAN Origin 을 CORS_ORIGINS 포트 기준으로 허용한다."""
        return cors_origin_regex(self.cors_origin_list)

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
