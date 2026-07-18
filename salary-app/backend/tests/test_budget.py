"""사업별 예산 미소진 '사유' 진단 단위 테스트 (F17 / Path A — 읽기 전용).

알고리즘은 그대로 두고, 잔여 예산이 왜 남았는지(인력 포화 vs 추가 여력)를 설명만 한다.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.services.budget import compute_budget_diagnostics
from app.services.distribute import MemberData, ProjectData

TODAY = date(2025, 1, 1)


def _proj(pid, budgets, start="2025-01-01", end="2025-12-31", name=None):
    return ProjectData(id=pid, name=name or pid, start_date=start, end_date=end, year_budgets=budgets)


def _part(member_id, project_id, rate, cost, start="2025-01-01", end="2025-12-31"):
    return SimpleNamespace(
        member_id=member_id, project_id=project_id, start_date=start, end_date=end, rate=rate, cost=cost
    )


def _by_id(diags):
    return {d.project_id: d for d in diags}


def test_fully_spent_is_ok():
    projects = [_proj("p1", {"2025": 12_000_000})]
    members = [MemberData(id="a", name="A", employ_type="정규직", rank="연구원", salary=1_000_000)]
    parts = [_part("a", "p1", 100, 12_000_000)]
    d = _by_id(compute_budget_diagnostics(projects, members, parts, TODAY))["p1"]
    assert d.reason == "ok"
    assert d.remaining < 1000


def test_no_budget():
    projects = [_proj("p1", {})]
    members = []
    d = _by_id(compute_budget_diagnostics(projects, members, [], TODAY))["p1"]
    assert d.reason == "no_budget"


def test_saturated_when_only_candidate_is_capped():
    """잔여 예산은 있지만, 유일한 미배정 연구원이 다른 사업에서 이미 월 100% → 인력 포화."""
    projects = [
        _proj("p1", {"2025": 50_000_000}),
        _proj("q", {"2025": 50_000_000}, end="2026-12-31"),  # q는 장기(카운트 대상)
    ]
    members = [
        MemberData(id="a", name="A", employ_type="정규직", rank="연구원", salary=1_000_000, max_rate=100),
        MemberData(id="b", name="B", employ_type="정규직", rank="연구원", salary=1_000_000, max_rate=100),
    ]
    parts = [
        _part("a", "p1", 10, 1_200_000),  # p1에 a가 10%만 → 잔여 큼
        _part("b", "q", 100, 12_000_000),  # b는 q에서 월 100% 풀가동 → p1에 못 들어감
    ]
    d = _by_id(compute_budget_diagnostics(projects, members, parts, TODAY))["p1"]
    assert d.reason == "saturated"
    assert d.recruitable == []


def test_slack_when_free_member_available():
    """잔여 예산 + 완전히 비어 있는 연구원 존재 → 추가 여력 있음."""
    projects = [_proj("p1", {"2025": 50_000_000})]
    members = [
        MemberData(id="a", name="A", employ_type="정규직", rank="연구원", salary=1_000_000),
        MemberData(id="free", name="여유", employ_type="정규직", rank="연구원", salary=1_000_000),
    ]
    parts = [_part("a", "p1", 10, 1_200_000)]  # free는 아무 데도 없음
    d = _by_id(compute_budget_diagnostics(projects, members, parts, TODAY))["p1"]
    assert d.reason == "slack"
    assert "여유" in d.recruitable
