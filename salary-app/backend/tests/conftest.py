"""
pytest 공용 픽스처.

- 인메모리 SQLite(`sqlite://` + StaticPool)로 격리 (AI-INSTRUCTIONS 5장).
- 운영 DB(salary.db)를 건드리지 않도록, main.py를 import하지 않고
  라우터만 모아 테스트 전용 FastAPI 앱을 구성한다.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.routers import members as members_router
from app.routers import projects as projects_router
from app.routers import participations as participations_router
from app.services.distribute import MemberData, ProjectData

# 라우터가 모든 모델을 import하므로 Base.metadata에 테이블이 등록된다.


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    app = FastAPI()
    app.include_router(members_router.router)
    app.include_router(projects_router.router)
    app.include_router(participations_router.router)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


# ── 배분 알고리즘 입력용 시드 데이터 (seed.py 상수 재사용) ──
@pytest.fixture
def algo_inputs():
    from seed import MEMBERS, PROJECTS

    members = [
        MemberData(
            id=m["id"],
            name=m["name"],
            employ_type=m["employ_type"],
            rank=m["rank"],
            salary=m["salary"],
            max_rate=m["max_rate"],
            max_projects=m["max_projects"],
            hire_date=m["hire_date"],
            resign_date=m["resign_date"],
        )
        for m in MEMBERS
    ]
    projects = [
        ProjectData(
            id=p["id"],
            name=p["name"],
            start_date=p["start_date"],
            end_date=p["end_date"],
            year_budgets={yr: float(v) for yr, v in p["year_budgets"].items()},
            required_chief=p["chief"],
            required_staff=list(p["staff"]),
            member_constraints={mid: float(r) for mid, r in p["constraints"].items()},
            member_months={},
        )
        for p in PROJECTS
    ]
    return members, projects
