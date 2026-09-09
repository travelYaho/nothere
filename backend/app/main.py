"""FastAPI 애플리케이션 진입점이다.

/api 라우터, CORS, health check, 공통 예외 응답을 한곳에서 설정한다.
서버 시작 시 Supabase Postgres 연결 가능 여부도 함께 확인한다.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError, ErrorCode
from app.db.session import check_db_connection

logger = logging.getLogger("yeogimalgo")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """앱 시작 시 DB 연결을 점검하고 종료 시점까지 컨텍스트를 유지한다."""
    try:
        check_db_connection()
        logger.info("Database connection OK")
    except Exception:
        logger.exception("Database connection failed. Check DATABASE_URL.")
    yield


app = FastAPI(
    title="여기말GO API",
    description="여행 일정 수정 서비스 백엔드",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    """프로세스 생존 여부를 확인하는 최소 health check."""
    return {"status": "ok"}


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """서비스 내부 AppError를 공통 {error:{code,message}} 형식으로 반환한다."""
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic 검증 오류를 프론트가 쓰기 쉬운 메시지로 변환한다."""
    first = exc.errors()[0] if exc.errors() else {}
    loc_parts = [str(part) for part in first.get("loc", []) if part not in {"body", "query", "path"}]
    field = loc_parts[-1] if loc_parts else None
    message = f"{field} 값이 올바르지 않습니다." if field else "요청 값이 올바르지 않습니다."
    return JSONResponse(
        status_code=422,
        content={"error": {"code": ErrorCode.VALIDATION_ERROR, "message": message}},
    )


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """예상하지 못한 DB 오류를 공통 에러 형식으로 감싼다."""
    logger.exception("Database error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": ErrorCode.DB_ERROR, "message": "데이터베이스 오류가 발생했습니다."}},
    )
