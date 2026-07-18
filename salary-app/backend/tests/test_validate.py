"""독립 검증기(validate.py, #7) 테스트.

핵심: ① 알고리즘의 정상 산출물은 위반 0건이어야 하고(교차 검증),
② 일부러 손상시킨 결과는 해당 유형의 위반이 검출되어야 한다(검증기 자체의 검증).
"""

from datetime import date

from app.services.distribute import (
    MemberData,
    ParticipationResult,
    ProjectData,
    auto_distribute,
)
from app.services.validate import audit_distribution

TODAY = date(2025, 1, 1)


def _member(mid="m1", **kw):
    defaults = dict(
        id=mid, name=mid, employ_type="정규직", rank="연구원",
        salary=3_000_000, max_rate=100.0, max_projects=5,
    )
    defaults.update(kw)
    return MemberData(**defaults)


def _proj(pid, **kw):
    defaults = dict(
        id=pid, name=pid, start_date="2025-01-01", end_date="2025-12-31",
        year_budgets={"2025": 100_000_000.0},
    )
    defaults.update(kw)
    return ProjectData(**defaults)


def _result(pid, mid, rate, cost, start="2025-01-01", end="2025-12-31", role="일반참여자"):
    return ParticipationResult(
        id="r-" + pid + mid, project_id=pid, member_id=mid, role=role,
        start_date=start, end_date=end, rate=rate, cost=cost,
    )


# ── ① 교차 검증: 알고리즘 산출물은 항상 위반 0건 ──


def test_seed_distribution_passes_audit(algo_inputs):
    """시드 데이터 전체 배분 결과가 독립 검증을 통과한다 (알고리즘 ↔ 검증기 교차 검증)."""
    members, projects = algo_inputs
    results = auto_distribute(projects, members, today=date(2025, 5, 18))
    assert audit_distribution(results, members, projects, date(2025, 5, 18)) == []


def test_mixed_funding_distribution_passes_audit():
    """정부수탁+기본사업 혼합(130% 특례 사용) 결과도 검증을 통과한다."""
    m = _member(max_projects=10)
    projects = [
        _proj("nat", sort_order=0),
        _proj("basic", sort_order=1, funding_source="기본사업"),
    ]
    results = auto_distribute(projects, [m], today=TODAY)
    assert audit_distribution(results, [m], projects, TODAY) == []


# ── ② 손상 검출: 유형별로 위반이 잡히는지 ──


def test_detects_rate_over_cap():
    m, p = _member(), _proj("p1")
    bad = [_result("p1", "m1", 60, 21_600_000), _result("p1b", "m1", 60, 21_600_000)]
    projects = [p, _proj("p1b")]
    found = audit_distribution(bad, [m], projects, TODAY)
    assert any("정부수탁 참여율 합" in v for v in found)


def test_detects_total_over_130():
    m = _member()
    projects = [_proj("b1", funding_source="기본사업"), _proj("b2", funding_source="기본사업")]
    bad = [_result("b1", "m1", 70, 25_200_000), _result("b2", "m1", 70, 25_200_000)]
    found = audit_distribution(bad, [m], projects, TODAY)
    assert any("전체 참여율 합" in v for v in found)


def test_detects_budget_overrun():
    m, p = _member(), _proj("p1", year_budgets={"2025": 1_000_000.0})
    bad = [_result("p1", "m1", 10, 3_600_000)]  # 예산 100만원인데 360만원 배분
    found = audit_distribution(bad, [m], [p], TODAY)
    assert any("총예산" in v for v in found)


def test_detects_below_minimum_rate():
    m, p = _member(), _proj("p1")
    bad = [_result("p1", "m1", 5, 1_800_000)]
    found = audit_distribution(bad, [m], [p], TODAY)
    assert any("최소 참여율" in v for v in found)


def test_detects_non_thousand_rounding():
    m, p = _member(), _proj("p1")
    bad = [_result("p1", "m1", 10, 3_600_500)]
    found = audit_distribution(bad, [m], [p], TODAY)
    assert any("천원 단위" in v for v in found)


def test_detects_three_chief_violation():
    m = _member(max_projects=10)
    projects = [_proj(f"p{i}", required_chief="m1") for i in range(1, 5)]
    bad = [_result(f"p{i}", "m1", 10, 3_600_000, role="연구책임자") for i in range(1, 5)]
    found = audit_distribution(bad, [m], projects, TODAY)
    assert any("3책" in v for v in found)


def test_detects_five_project_violation():
    m = _member(max_projects=2)
    projects = [_proj(f"p{i}") for i in range(1, 4)]
    bad = [_result(f"p{i}", "m1", 10, 3_600_000) for i in range(1, 4)]
    found = audit_distribution(bad, [m], projects, TODAY)
    assert any("5공" in v for v in found)


def test_detects_out_of_period_assignment():
    m, p = _member(), _proj("p1", start_date="2025-03-01")
    bad = [_result("p1", "m1", 10, 3_600_000, start="2025-01-01")]  # 사업 시작 전부터 배정
    found = audit_distribution(bad, [m], [p], TODAY)
    assert any("사업기간" in v for v in found)


def test_detects_overstated_cost():
    m, p = _member(), _proj("p1")
    bad = [_result("p1", "m1", 10, 10_000_000)]  # 급여×개월×10% = 360만원인데 1000만원 계상
    found = audit_distribution(bad, [m], [p], TODAY)
    assert any("초과 계상" in v for v in found)
