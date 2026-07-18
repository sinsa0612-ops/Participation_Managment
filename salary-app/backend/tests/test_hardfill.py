"""하드 순차 우선순위 채움 테스트.

설계: 필수(연구책임자/실무자)·강제(member_months) 인원은 모든 사업에 10% 예약(보장).
그다음 우선순위 순서대로 사업을 하나씩 '예산까지' 채운 뒤 다음 사업으로 → 1순위가 인력을 먼저 통째로 가져간다.
"""

from __future__ import annotations

from datetime import date

from app.services.distribute import MemberData, ProjectData, auto_distribute

TODAY = date(2025, 1, 1)


def _m(mid, salary=1_000_000, max_rate=100, max_projects=5):
    return MemberData(id=mid, name=mid, employ_type="정규직", rank="연구원",
                      salary=salary, max_rate=max_rate, max_projects=max_projects)


def _p(pid, sort_order, budget, chief=None):
    return ProjectData(id=pid, name=pid, start_date="2025-01-01", end_date="2025-12-31",
                       year_budgets={"2025": float(budget)}, required_chief=chief, sort_order=sort_order)


def test_top_priority_consumes_member_before_lower():
    """일반 연구원 1명·두 사업 모두 예산 충분 → 1순위가 100%까지 가져가고 2순위는 굶는다."""
    m = _m("a")  # 어느 사업에도 필수가 아닌 일반 연구원
    p1 = _p("p1", 0, 12_000_000)  # 1순위: 예산 = m의 100%×12개월
    p2 = _p("p2", 1, 12_000_000)  # 2순위
    res = auto_distribute([p1, p2], [m], today=TODAY)
    r1 = next((r for r in res if r.project_id == "p1"), None)
    assert r1 is not None and r1.rate == 100  # 1순위가 m을 100% 선점
    assert not any(r.project_id == "p2" for r in res)  # 2순위는 굶음(일반 연구원 안 남음)


def test_required_guaranteed_in_starved_low_project():
    """필수 연구원은 1순위가 거의 다 먹어도 하위 사업에서 최소 10%로 보장된다."""
    a = _m("a")
    p1 = _p("p1", 0, 100_000_000, chief="a")  # 1순위(예산 큼)
    p2 = _p("p2", 1, 100_000_000, chief="a")  # 하위지만 a가 필수
    res = auto_distribute([p1, p2], [a], today=TODAY)
    r1 = next(r for r in res if r.project_id == "p1")
    r2 = next(r for r in res if r.project_id == "p2")
    assert r1.rate == 90  # P2 예약 10% 때문에 P1은 90%까지
    assert r2.rate == 10  # 하위 사업이지만 필수 a는 10% 보장


def test_lower_priority_gets_leftover_capacity():
    """1순위 예산이 작으면 다 채우고 남은 인력은 2순위로 흘러간다."""
    m = _m("a")
    p1 = _p("p1", 0, 6_000_000)  # 1순위: m의 50%면 소진(1M×12×50%)
    p2 = _p("p2", 1, 12_000_000)  # 2순위
    res = auto_distribute([p1, p2], [m], today=TODAY)
    r1 = next(r for r in res if r.project_id == "p1")
    r2 = next((r for r in res if r.project_id == "p2"), None)
    assert r1.rate == 50  # 1순위는 예산만큼만(50%)
    assert r2 is not None and r2.rate == 50  # 남은 50%는 2순위로
