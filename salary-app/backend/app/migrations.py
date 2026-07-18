"""경량 자동 스키마 마이그레이션 (SQLite, 추가형 변경 전용).

배경:
    `Base.metadata.create_all()`은 *없는 테이블만* 새로 만든다. 이미 존재하는
    테이블에 모델이 새로 추가한 컬럼(예: projects.sort_order)은 반영하지 못한다.
    그래서 구버전에서 만들어진 DB로 신버전 코드를 돌리면
    `sqlite3.OperationalError: no such column ...` → 500 으로 기능이 깨진다.
    ("실행은 되는데 기능이 작동하지 않는" 증상의 실제 원인.)

이 모듈은 시작 시 모델과 실제 DB 스키마를 대조해 누락된
    (1) 테이블 → create_all 로 생성
    (2) 컬럼  → ALTER TABLE ADD COLUMN 으로 추가
한다. SQLite가 안전하게 지원하는 것은 추가형 변경뿐이므로, 컬럼 삭제·타입 변경은
다루지 않는다(해당 케이스가 생기면 Alembic 도입). 단일 사용자 SQLite 앱에는 충분하다.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import Base

log = logging.getLogger("salary-app")

_NUMERIC_HINTS = ("INT", "FLOAT", "REAL", "NUM", "DEC", "DOUBLE")


def _default_literal(col, coltype_upper: str) -> str:
    """ALTER TABLE ADD COLUMN 에 쓸 DEFAULT 리터럴을 만든다."""
    server_default = getattr(col, "server_default", None)
    if server_default is not None and getattr(server_default, "arg", None) is not None:
        arg = server_default.arg
        value = getattr(arg, "text", None)
        if value is None:
            value = str(arg)
        value = value.strip()
        if any(h in coltype_upper for h in _NUMERIC_HINTS):
            return value
        if value.startswith("'"):
            return value
        return "'" + value.replace("'", "''") + "'"
    # server_default 가 없는 NOT NULL 컬럼 → 타입에 맞는 안전한 기본값
    if any(h in coltype_upper for h in _NUMERIC_HINTS):
        return "0"
    return "''"


def auto_migrate(engine: Engine) -> list[str]:
    """누락 테이블/컬럼을 기존 DB에 반영한다. 적용한 DDL 목록을 반환한다."""
    # 1) 누락 테이블 생성
    Base.metadata.create_all(bind=engine)

    # 2) 기존 테이블의 누락 컬럼 추가
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    dialect = engine.dialect
    applied: list[str] = []

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # 방금 create_all 이 만든 테이블 — 컬럼이 이미 완비됨
            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing_cols:
                    continue
                coltype = col.type.compile(dialect=dialect)
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {coltype}'
                if not col.nullable:
                    ddl += f" NOT NULL DEFAULT {_default_literal(col, coltype.upper())}"
                elif col.server_default is not None:
                    ddl += f" DEFAULT {_default_literal(col, coltype.upper())}"
                log.info("자동 마이그레이션: %s", ddl)
                conn.execute(text(ddl))
                applied.append(ddl)

    if applied:
        log.info("자동 마이그레이션 완료 — 컬럼 %d개 추가됨", len(applied))
    return applied
