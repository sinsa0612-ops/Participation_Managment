"""단장(rank=단장) 상한 하드 강제 테스트 (#1).

단장은 '잔여 6개월 미만 사업 제외' 예외를 적용하지 않고 동시 참여 사업을 전부 카운트한다.
→ max_projects를 단기 사업까지 포함해 절대 초과하지 않는다.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.services.distribute import (
    MemberData,
    ProjectData,
    auto_distribute,
    counts_toward_concurrency,
)
from app.services.stats import compute_member_stats

TODAY = date(2025, 1, 1)


def test_counts_toward_concurrency_director_counts_short():
    # 단기 사업(잔여 2개월) — 일반 연구원은 제외, 단장은 카운트
    assert counts_toward_concurrency("연구원", "2025-03-31", TODAY) is False
    assert counts_toward_concurrency("단장", "2025-03-31", TODAY) is True
    # 장기 사업은 둘 다 카운트
    assert counts_toward_concurrency("연구원", "2026-12-31", TODAY) is True
    assert counts_toward_concurrency("단장", "2026-12-31", TODAY) is True


def test_director_max_concurrent_counts_short_projects():
    """단장이 단기 1 + 장기 1에 동시 참여 → 동시참여 2로 집계(상한 1이면 초과)."""
    members = [
        SimpleNamespace(
            id="d", name="단장", employ_type="정규직", rank="단장", salary=1_000_000, max_rate=100, max_projects=1
        ),
    ]
    projects = [SimpleNamespace(id="long", end_date="2026-12-31"), SimpleNamespace(id="short", end_date="2025-03-31")]
    parts = [
        SimpleNamespace(
            member_id="d", project_id="long", start_date="2025-01-01", end_date="2025-12-31", rate=10, cost=0
        ),
        SimpleNamespace(
            member_id="d", project_id="short", start_date="2025-01-01", end_date="2025-03-31", rate=10, cost=0
        ),
    ]
    s = compute_member_stats(members, parts, projects, TODAY)[0]
    assert s.max_concurrent == 2  # 단장은 단기 사업도 카운트
    assert s.status == "초과"  # max_projects=1 초과


def test_director_gate_blocks_extra_project():
    """단장 max_projects=1: 어느 달에도 동시 참여(단기 사업 포함 카운트)가 1개를 넘지 않는다.

    부분기간(연속 가용 구간) 배정이 도입되면서, 단기 사업이 끝난 뒤의 달에는 장기 사업에
    참여할 수 있다(순차 참여). 따라서 '생애 사업 수 ≤ 1'이 아니라 '월별 동시참여 ≤ 1'을 보장한다(F5).
    """
    from app.services.distribute import _to_month_idx, counts_toward_concurrency

    members = [
        MemberData(
            id="d", name="단장", employ_type="정규직", rank="단장", salary=1_000_000, max_rate=100, max_projects=1
        ),
    ]
    projects = [
        ProjectData(
            id="long",
            name="장기",
            start_date="2025-01-01",
            end_date="2026-12-31",
            year_budgets={"2025": 50_000_000, "2026": 50_000_000},
            required_chief="d",
        ),
        ProjectData(
            id="short",
            name="단기",
            start_date="2025-01-01",
            end_date="2025-03-31",
            year_budgets={"2025": 50_000_000},
            required_chief="d",
        ),
    ]
    results = auto_distribute(projects, members, today=TODAY)
    proj_end = {p.id: p.end_date for p in projects}
    mine = [r for r in results if r.member_id == "d"]
    # 어느 달에도 카운트 대상 동시참여 사업 수 ≤ max_projects(1)
    for mi in range(_to_month_idx("2025-01-01"), _to_month_idx("2026-12-01") + 1):
        concurrent = {
            r.project_id
            for r in mine
            if _to_month_idx(r.start_date) <= mi <= _to_month_idx(r.end_date)
            and counts_toward_concurrency("단장", proj_end[r.project_id], TODAY)
        }
        assert len(concurrent) <= 1
