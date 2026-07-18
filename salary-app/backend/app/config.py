"""
설정 중앙화 (AI-INSTRUCTIONS 2-1).

환경 의존 값(DB 경로·포트·CORS·기준일)은 이 단일 출처에서만 가져온다.
비밀/환경별 값은 `.env`로 주입하며, `.env`는 `.gitignore`에 포함한다.
프로젝트 루트는 절대경로를 박지 않고 `__file__` 기준으로 동적 산출한다.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_frozen() -> bool:
    """PyInstaller로 패키징되어 실행 중인지 여부."""
    return bool(getattr(sys, "frozen", False))


def _default_database_url() -> str:
    """패키징 실행 시 DB를 쓰기 가능한 로컬 앱데이터에 둔다.

    - 설치 경로(예: Program Files)는 읽기 전용일 수 있으므로 exe 옆에 DB를 두면 안 된다.
    - Roaming(%APPDATA%)은 OneDrive/도메인 동기화로 SQLite 잠금·손상이 날 수 있어,
      동기화되지 않는 %LOCALAPPDATA%를 우선 사용한다.
    - 개발 중에는 기존처럼 작업 디렉터리의 salary.db를 사용한다.
    """
    if _is_frozen():
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or Path.home()
        base = Path(root) / "salary-app"
        base.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{(base / 'salary.db').as_posix()}"
    return "sqlite:///./salary.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # backend/ 디렉터리 (이 파일의 상위의 상위)
    project_root: Path = Path(__file__).resolve().parent.parent

    database_url: str = _default_database_url()
    server_port: int = 8001
    cors_origins: list[str] = ["*"]

    # 배분 알고리즘 기준일. 미설정 시 '실제 오늘'을 사용한다.
    # (과거에는 코드에 2026-05-18로 하드코딩되어 시간이 지날수록 오작동했음 — F1)
    base_date: date = date.today()

    @property
    def frontend_dir(self) -> Path:
        """서빙할 프론트엔드 빌드(dist) 경로. 패키징 시 _MEIPASS에 번들된 frontend_dist를 가리킨다."""
        if _is_frozen():
            return Path(getattr(sys, "_MEIPASS", ".")) / "frontend_dist"
        return self.project_root.parent / "frontend" / "dist"


settings = Settings()
