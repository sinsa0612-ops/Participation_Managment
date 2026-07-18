"""
프로토타입(salary_distribution.tsx)의 초기 Mock 데이터를 DB에 투입하는 시드 스크립트.
실행: uv run python seed.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base
from app.ids import new_id
from app.models.member import Member
from app.models.project import Project, ProjectBudget, ProjectRequirement, ProjectConstraint

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

MEMBERS = [
    {"id": "m1",  "name": "김단장", "employ_type": "정규직", "rank": "단장",   "salary": 6000000, "max_rate": 100, "max_projects": 5, "hire_date": "2020-03-01", "resign_date": None, "birth_date": "1975-04-12", "researcher_no": "10012345"},
    {"id": "m2",  "name": "이센터", "employ_type": "정규직", "rank": "센터장", "salary": 5000000, "max_rate": 100, "max_projects": 5, "hire_date": "2019-07-01", "resign_date": None, "birth_date": "1978-09-23", "researcher_no": "10023456"},
    {"id": "m3",  "name": "박팀장", "employ_type": "정규직", "rank": "팀장",   "salary": 4500000, "max_rate": 80,  "max_projects": 4, "hire_date": "2021-01-01", "resign_date": None, "birth_date": "1982-02-07", "researcher_no": "10034567"},
    {"id": "m4",  "name": "최팀장", "employ_type": "전문직", "rank": "팀장",   "salary": 4000000, "max_rate": 100, "max_projects": 5, "hire_date": "2022-04-01", "resign_date": None, "birth_date": "1984-11-30", "researcher_no": "10045678"},
    {"id": "m5",  "name": "정연구", "employ_type": "정규직", "rank": "연구원", "salary": 3500000, "max_rate": 100, "max_projects": 5, "hire_date": "2023-01-01", "resign_date": None, "birth_date": "1990-06-15", "researcher_no": "10056789"},
    {"id": "m6",  "name": "한연구", "employ_type": "전문직", "rank": "연구원", "salary": 3200000, "max_rate": 60,  "max_projects": 3, "hire_date": "2023-06-01", "resign_date": None, "birth_date": "1988-03-22", "researcher_no": "10067890"},
    {"id": "m7",  "name": "윤연구", "employ_type": "정규직", "rank": "연구원", "salary": 3000000, "max_rate": 100, "max_projects": 5, "hire_date": "2024-01-01", "resign_date": None, "birth_date": "1993-08-01", "researcher_no": "10078901"},
    {"id": "m8",  "name": "장연구", "employ_type": "위촉직", "rank": "연구원", "salary": 2800000, "max_rate": 100, "max_projects": 5, "hire_date": "2024-03-01", "resign_date": None, "birth_date": "1991-12-19", "researcher_no": "10089012"},
    {"id": "m9",  "name": "오연구", "employ_type": "위촉직", "rank": "연구원", "salary": 2500000, "max_rate": 100, "max_projects": 5, "hire_date": "2024-06-01", "resign_date": "2025-09-30", "birth_date": "1995-05-08", "researcher_no": "10090123"},
    {"id": "m10", "name": "임연구", "employ_type": "위촉직", "rank": "연구원", "salary": 2500000, "max_rate": 50,  "max_projects": 2, "hire_date": "2025-01-01", "resign_date": None, "birth_date": "1997-10-27", "researcher_no": "10101234"},
]

PROJECTS = [
    {
        "id": "p1", "name": "스마트시티 AI 플랫폼 개발",
        "start_date": "2025-01-01", "end_date": "2026-06-30",
        "year_budgets": {"2025": 125000000, "2026": 63000000},
        "chief": "m1", "staff": ["m3"],
        "constraints": {"m6": 30},
    },
    {
        "id": "p2", "name": "친환경 에너지 효율화 연구",
        "start_date": "2025-03-01", "end_date": "2026-02-28",
        "year_budgets": {"2025": 80000000, "2026": 23000000},
        "chief": "m2", "staff": ["m4"],
        "constraints": {"m10": 20},
    },
    {
        "id": "p3", "name": "디지털 헬스케어 플랫폼",
        "start_date": "2025-04-01", "end_date": "2025-12-31",
        "year_budgets": {"2025": 71000000},
        "chief": "m2", "staff": ["m5"],
        "constraints": {},
    },
    {
        "id": "p4", "name": "자율주행 안전 시스템 구축",
        "start_date": "2025-06-01", "end_date": "2026-12-31",
        "year_budgets": {"2025": 57000000, "2026": 67000000},
        "chief": "m1", "staff": ["m4", "m5"],
        "constraints": {"m8": 40},
    },
    {
        "id": "p5", "name": "바이오 데이터 분석 고도화",
        "start_date": "2025-07-01", "end_date": "2026-03-31",
        "year_budgets": {"2025": 46000000, "2026": 19000000},
        "chief": "m3", "staff": ["m6"],
        "constraints": {},
    },
    {
        "id": "p6", "name": "스마트 물류 최적화 시스템",
        "start_date": "2025-09-01", "end_date": "2026-08-31",
        "year_budgets": {"2025": 34000000, "2026": 40000000},
        "chief": "m2", "staff": ["m7"],
        "constraints": {"m10": 30},
    },
    {
        "id": "p7", "name": "공공 빅데이터 활용 연구",
        "start_date": "2026-01-01", "end_date": "2026-12-31",
        "year_budgets": {"2026": 89000000},
        "chief": "m1", "staff": ["m3", "m4"],
        "constraints": {},
    },
]


def seed():
    db = SessionLocal()
    try:
        # 기존 데이터 초기화
        for model in [ProjectConstraint, ProjectRequirement, ProjectBudget, Project, Member]:
            db.query(model).delete()

        for m in MEMBERS:
            db.add(Member(**m))

        for p in PROJECTS:
            db.add(Project(id=p["id"], name=p["name"], start_date=p["start_date"], end_date=p["end_date"]))
            for yr, total in p["year_budgets"].items():
                db.add(ProjectBudget(id=new_id(), project_id=p["id"], year=yr, amount=total))
            if p["chief"]:
                db.add(ProjectRequirement(id=new_id(), project_id=p["id"], member_id=p["chief"], role="chief"))
            for mid in p["staff"]:
                db.add(ProjectRequirement(id=new_id(), project_id=p["id"], member_id=mid, role="staff"))
            for mid, rate in p["constraints"].items():
                db.add(ProjectConstraint(id=new_id(), project_id=p["id"], member_id=mid, max_rate=rate))

        db.commit()
        logger.info("Seed OK: %d members, %d projects", len(MEMBERS), len(PROJECTS))
    finally:
        db.close()


if __name__ == "__main__":
    seed()
