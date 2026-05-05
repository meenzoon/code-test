"""DB 도구 — 다중 SQLite 소스에 대한 스키마 introspection 및 read-only SQL 실행.

환경변수
    DB_SOURCES   "name1=path1,name2=path2" 형태. 예: "sales=./sales.db,crm=./crm.db"
    DB_DEFAULT   기본 소스 이름. 미설정 시 DB_SOURCES의 첫 번째 항목 사용.

다른 백엔드(Postgres/MySQL)로 확장하려면 _connect()를 SQLAlchemy create_engine으로 교체한다.
"""

import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from langchain_core.tools import tool

# SELECT / WITH(=CTE) / EXPLAIN 으로 시작하는 쿼리만 허용한다 (read-only 보장)
_READONLY_PREFIX = re.compile(r"^\s*(select|with|explain)\b", re.IGNORECASE)
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|replace|pragma|vacuum)\b",
    re.IGNORECASE,
)
_MAX_ROWS = 100


def _load_sources() -> dict[str, str]:
    raw = os.getenv("DB_SOURCES", "").strip()
    if not raw:
        return {}
    out: dict[str, str] = {}
    for item in raw.split(","):
        if "=" not in item:
            continue
        name, path = item.split("=", 1)
        out[name.strip()] = path.strip()
    return out


def _resolve(source: str | None) -> tuple[str, str]:
    """소스 이름을 (name, path)로 해석한다. 미지정 시 DB_DEFAULT 또는 첫 항목."""
    sources = _load_sources()
    if not sources:
        raise ValueError(
            "DB_SOURCES 환경변수가 비어 있습니다. 'name=path,...' 형식으로 설정하세요."
        )
    if source is None:
        source = os.getenv("DB_DEFAULT") or next(iter(sources))
    if source not in sources:
        raise ValueError(f"알 수 없는 DB 소스: {source!r}. 사용 가능: {list(sources)}")
    return source, sources[source]


def _connect(path: str) -> sqlite3.Connection:
    if not Path(path).exists():
        raise FileNotFoundError(f"DB 파일을 찾을 수 없습니다: {path}")
    # uri=True + mode=ro 로 OS 레벨에서도 read-only 보장
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@tool
def list_db_sources() -> str:
    """등록된 DB 소스 이름과 경로 목록을 반환한다."""
    sources = _load_sources()
    if not sources:
        return "(no DB sources configured — set DB_SOURCES env var)"
    return "\n".join(f"{name}: {path}" for name, path in sources.items())


@tool
def list_tables(source: str | None = None) -> str:
    """주어진 DB 소스의 테이블 이름 목록을 반환한다. source 미지정 시 기본 소스 사용."""
    try:
        name, path = _resolve(source)
        with closing(_connect(path)) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        tables = [r["name"] for r in rows]
        return f"[{name}] " + (", ".join(tables) if tables else "(no tables)")
    except Exception as e:
        return f"Error: {e}"


@tool
def describe_table(table: str, source: str | None = None) -> str:
    """지정한 테이블의 컬럼 스키마(이름/타입/NULL 허용 여부)를 반환한다."""
    try:
        name, path = _resolve(source)
        # 테이블 이름은 식별자 검증 (SQL injection 방지)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            return f"Error: invalid table name {table!r}"
        with closing(_connect(path)) as conn:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not rows:
            return f"[{name}] table {table!r} not found"
        lines = [
            f"{r['name']}\t{r['type']}\t{'NULL' if not r['notnull'] else 'NOT NULL'}"
            for r in rows
        ]
        return f"[{name}.{table}]\n" + "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@tool
def run_sql_readonly(sql: str, source: str | None = None) -> str:
    """SELECT / WITH / EXPLAIN 쿼리만 실행한다. 결과는 최대 100행까지 반환된다.

    쓰기 계열 키워드(INSERT/UPDATE/DELETE/DROP 등)가 포함되면 거부한다.
    """
    try:
        if not _READONLY_PREFIX.match(sql):
            return "Error: only SELECT / WITH / EXPLAIN queries are allowed"
        if _FORBIDDEN.search(sql):
            return "Error: query contains forbidden write keyword"
        name, path = _resolve(source)
        with closing(_connect(path)) as conn:
            cursor = conn.execute(sql)
            rows = cursor.fetchmany(_MAX_ROWS + 1)
            cols = [d[0] for d in cursor.description] if cursor.description else []
        truncated = len(rows) > _MAX_ROWS
        rows = rows[:_MAX_ROWS]
        if not cols:
            return f"[{name}] (no result columns)"
        header = "\t".join(cols)
        body = "\n".join("\t".join(str(r[c]) for c in cols) for r in rows)
        suffix = (
            f"\n... ({_MAX_ROWS}+ rows truncated)"
            if truncated
            else f"\n({len(rows)} rows)"
        )
        return f"[{name}]\n{header}\n{body}{suffix}"
    except Exception as e:
        return f"Error: {e}"


# DB 에이전트에 등록할 도구 목록
DB_TOOLS = [list_db_sources, list_tables, describe_table, run_sql_readonly]
