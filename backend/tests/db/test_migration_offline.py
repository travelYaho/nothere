"""0002 마이그레이션이 DB 연결 없이도 유효한 SQL 로 렌더링되는지 확인한다.

alembic 오프라인 모드(`--sql`)는 실제 접속 없이 SQL 문자열만 만들기 때문에,
지금처럼 Supabase 연결이 막혀 있어도 마이그레이션 문법/의존순서(FK 참조 테이블이
먼저 생성되는지 등) 오류는 미리 잡을 수 있다.
"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def test_upgrade_head_renders_offline_sql_without_db_connection():
    # 시드 데이터에 한글이 포함돼 있어, 콘솔 코드페이지(cp949 등)에 좌우되지
    # 않도록 자식 프로세스의 표준출력 인코딩을 명시적으로 UTF-8 로 고정한다.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic.config", "upgrade", "0001_init:head", "--sql"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr

    sql = result.stdout
    # 새 테이블이 전부 생성되는지, 그리고 참조 대상(FK) 이 먼저 만들어지는 순서인지 확인한다.
    for table in [
        "regions",
        "experience_tags",
        "places",
        "place_experience_tags",
        "trips",
        "trip_preferred_experiences",
        "trip_places",
        "trip_place_purposes",
        "user_long_term_preferences",
        "share_link",
        "guide_entry",
        "guide_like",
    ]:
        assert f"CREATE TABLE {table} " in sql, f"{table} 테이블 생성 SQL이 없습니다."

    assert sql.index("CREATE TABLE regions ") < sql.index("CREATE TABLE places ")
    assert sql.index("CREATE TABLE places ") < sql.index("CREATE TABLE trip_places ")
    assert sql.index("CREATE TABLE trips ") < sql.index("CREATE TABLE trip_places ")
    assert sql.index("CREATE TABLE trips ") < sql.index("CREATE TABLE share_link ")
    assert sql.index("CREATE TABLE share_link ") < sql.index("CREATE TABLE guide_like ")
    assert "DROP TABLE schedules" in sql
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql
