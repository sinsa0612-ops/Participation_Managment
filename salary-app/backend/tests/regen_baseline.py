"""특성화 baseline 재생성 — 연도별 세그먼트 배분(예산 끝까지 소진) 도입에 따른 의도된 동작 변경 반영.

실행: uv run python tests/regen_baseline.py  (또는 .venv 파이썬으로 backend 디렉터리에서)
사용자 승인 하에만 실행한다. test_distribution_matches_baseline 의 입력·정규화와 동일해야 한다.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.distribute import MemberData, ProjectData, auto_distribute  # noqa: E402
from seed import MEMBERS, PROJECTS  # noqa: E402

BASE_DATE = date(2026, 5, 18)
BASELINE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseline_distribution.json")


def _normalize(results):
    return sorted(
        [
            {
                "project_id": r.project_id,
                "member_id": r.member_id,
                "role": r.role,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "rate": r.rate,
                "cost": r.cost,
            }
            for r in results
        ],
        key=lambda x: (x["project_id"], x["member_id"], x["start_date"]),
    )


def main():
    members = [
        MemberData(
            id=m["id"], name=m["name"], employ_type=m["employ_type"], rank=m["rank"], salary=m["salary"],
            max_rate=m["max_rate"], max_projects=m["max_projects"], hire_date=m["hire_date"], resign_date=m["resign_date"],
        )
        for m in MEMBERS
    ]
    projects = [
        ProjectData(
            id=p["id"], name=p["name"], start_date=p["start_date"], end_date=p["end_date"],
            year_budgets={yr: float(v) for yr, v in p["year_budgets"].items()},
            required_chief=p["chief"], required_staff=list(p["staff"]),
            member_constraints={mid: float(r) for mid, r in p["constraints"].items()}, member_months={},
        )
        for p in PROJECTS
    ]
    snapshot = _normalize(auto_distribute(projects, members, today=BASE_DATE))
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print(f"baseline 재생성: {len(snapshot)}건 → {BASELINE_PATH}")


if __name__ == "__main__":
    main()
