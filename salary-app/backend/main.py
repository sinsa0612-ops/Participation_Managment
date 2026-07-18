from __future__ import annotations

import logging
import os
import socket
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine
from app.migrations import auto_migrate
from app.routers import members, projects, participations

log = logging.getLogger("salary-app")


def _data_dir() -> Path:
    """쓰기 가능한 사용자별 데이터 폴더(%LOCALAPPDATA%\\salary-app)."""
    root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    d = Path(root) / "salary-app"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _setup_logging() -> Path:
    """파일 + 콘솔 로깅을 구성한다.

    배포된 다른 PC에서 "기능이 작동하지 않는" 원인을 추적할 수 있도록,
    모든 서버/API 오류를 사용자별 로그 파일에 남긴다. uvicorn 로거도 root로
    전파시켜 같은 파일에 기록되게 한다(log_config=None).
    """
    log_dir = _data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    return log_path


def create_app() -> FastAPI:
    """FastAPI 앱을 생성하고 라우터/정적파일을 마운트한다."""
    # 구버전 DB와의 스키마 드리프트(누락 컬럼/테이블)를 시작 시 자동 보정한다.
    auto_migrate(engine)

    app = FastAPI(
        title="사업비 인건비 배분 API",
        description="정부 과제 참여 연구원의 인건비 자동 배분 관리 시스템",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(members.router)
    app.include_router(projects.router)
    app.include_router(participations.router)

    # 동작 점검용 헬스 엔드포인트 (정적 마운트 이전에 등록해야 / 보다 우선 매칭)
    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": "1.0.0", "db": settings.database_url}

    # 단일 exe 배포 시: 백엔드가 빌드된 React(dist)를 직접 서빙한다.
    # API 라우트 등록 후에 마운트해야 /members 등 API 경로가 우선 매칭된다.
    frontend_dir = settings.frontend_dir
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
    else:
        log.warning("프론트엔드 빌드 폴더를 찾을 수 없습니다: %s", frontend_dir)

    return app


# 모듈 레벨 app — 개발 시 `uvicorn main:app --reload` 호환용.
app = create_app()


def _find_free_port(preferred: int, attempts: int = 20) -> int:
    """선호 포트가 점유돼 있으면 다음 빈 포트를 찾는다(다른 PC의 포트 충돌 대비)."""
    for port in [preferred, *range(preferred + 1, preferred + attempts)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def main():
    """패키징된 실행 진입점 — 서버를 기동하고 기본 브라우저로 앱을 연다.

    시작 단계의 모든 예외를 로그로 남기고, 오류 시 콘솔을 닫지 않아
    비개발자도 화면/로그로 원인을 전달할 수 있게 한다.
    """
    import threading
    import webbrowser

    import uvicorn

    log_path = _setup_logging()
    try:
        port = _find_free_port(settings.server_port)
        url = f"http://127.0.0.1:{port}"

        log.info("인건비 배분 서버 시작 — %s", url)
        log.info("DB: %s", settings.database_url)
        log.info("프론트엔드: %s", settings.frontend_dir)

        print("\n" + "=" * 56)
        print("  인건비 배분 프로그램이 실행 중입니다.")
        print(f"  브라우저 주소:  {url}")
        print("  창이 자동으로 열리지 않으면 위 주소를 브라우저에 입력하세요.")
        print("  ※ 이 검은 창을 닫으면 프로그램이 종료됩니다.")
        print("=" * 56 + "\n")

        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
        # log_config=None: uvicorn 로그를 우리 root 핸들러(파일)로 전파시킨다.
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", log_config=None)
    except Exception:
        log.exception("서버 시작 중 오류가 발생했습니다")
        print("\n[오류] 프로그램을 시작하지 못했습니다.")
        print(f"로그 파일을 확인하거나 관리자에게 전달하세요:\n  {log_path}")
        try:
            input("\n엔터 키를 누르면 창이 닫힙니다...")
        except EOFError:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
