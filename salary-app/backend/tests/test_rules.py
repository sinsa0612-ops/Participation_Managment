"""3책(#5)·재원별 상한 130% 특례(#6) 규칙 테스트.

- 3책: '주관 사업의 연구책임자'로는 동시 3개까지만 배정된다. 참여기관 사업은 카운트 제외.
- 130%: 정부수탁 합산은 월 100%(개인 max_rate) 상한, 기본사업 포함 전체는 130%까지.
"""

from datetime import date

from app.services.distribute import MemberData, ProjectData, auto_distribute

TODAY = date(2025, 1, 1)
BIG_BUDGET = {"2025": 500_000_000.0}


def _member(mid="m1", **kw):
    defaults = dict(
        id=mid,
        name=mid,
        employ_type="정규직",
        rank="연구원",
        salary=3_000_000,
        max_rate=100.0,
        max_projects=10,  # 5공 게이트가 끼어들지 않게 넉넉히
    )
    defaults.update(kw)
    return MemberData(**defaults)


def _proj(pid, order, chief=None, org_role="주관", funding_source="정부수탁"):
    return ProjectData(
        id=pid,
        name=pid,
        start_date="2025-01-01",
        end_date="2025-12-31",
        year_budgets=dict(BIG_BUDGET),
        required_chief=chief,
        sort_order=order,
        org_role=org_role,
        funding_source=funding_source,
    )


# ── 3책 (#5) ──────────────────────────────────────


def test_chief_capped_at_three_lead_projects():
    """주관 사업 4개의 연구책임자 → 3개까지만 배정된다."""
    m = _member()
    projects = [_proj(f"p{i}", i, chief="m1") for i in range(1, 5)]
    results = auto_distribute(projects, [m], today=TODAY)

    assigned = {r.project_id for r in results if r.member_id == "m1" and r.role == "연구책임자"}
    assert assigned == {"p1", "p2", "p3"}  # 우선순위 순으로 3개, p4는 3책 초과로 차단


def test_partner_project_not_counted_for_chief_cap():
    """참여기관(org_role=참여) 사업의 책임자는 3책에 카운트되지 않는다 → 4개 모두 배정."""
    m = _member()
    projects = [_proj(f"p{i}", i, chief="m1") for i in range(1, 4)]
    projects.append(_proj("p4", 4, chief="m1", org_role="참여"))
    results = auto_distribute(projects, [m], today=TODAY)

    assigned = {r.project_id for r in results if r.member_id == "m1"}
    assert assigned == {"p1", "p2", "p3", "p4"}


def test_chief_cap_ignores_ordinary_participation():
    """일반참여자로 참여하는 주관 사업은 3책과 무관하다 (5공만 적용)."""
    m = _member()
    # 책임자 아님(일반참여) 3개 + 책임자 3개 → 책임자 3개 전부 배정 가능해야 함
    projects = [_proj(f"g{i}", i) for i in range(3)]  # chief=None → 일반참여
    projects += [_proj(f"c{i}", 10 + i, chief="m1") for i in range(3)]
    results = auto_distribute(projects, [m], today=TODAY)

    chief_projects = {r.project_id for r in results if r.role == "연구책임자"}
    assert chief_projects == {"c0", "c1", "c2"}


# ── 재원별 상한 (#6) ──────────────────────────────


def test_basic_project_allows_up_to_130_total():
    """정부수탁 100% 소진 후에도 기본사업으로 30%p 추가 계상(전체 130%)이 가능하다."""
    m = _member()
    nat = _proj("nat", 0)  # 정부수탁 — 먼저 채움
    basic = _proj("basic", 1, funding_source="기본사업")
    results = auto_distribute([nat, basic], [m], today=TODAY)

    by_pid = {r.project_id: r for r in results}
    assert by_pid["nat"].rate == 100.0  # 국비 상한까지 소진
    assert by_pid["basic"].rate == 30.0  # 전체 130% 상한까지의 잔여분


def test_nat_projects_still_capped_at_100():
    """정부수탁 사업만 있으면 월 합산 100%를 넘지 않는다 (130% 특례는 기본사업 전용)."""
    m = _member()
    projects = [_proj("n1", 0), _proj("n2", 1)]
    results = auto_distribute(projects, [m], today=TODAY)

    total = sum(r.rate for r in results if r.member_id == "m1")
    assert total <= 100.0


def test_basic_only_capped_at_130():
    """기본사업 단독이면 130%까지 계상 가능하다 (max_rate=국비 상한은 미적용)."""
    m = _member()
    projects = [_proj("b1", 0, funding_source="기본사업"), _proj("b2", 1, funding_source="기본사업")]
    results = auto_distribute(projects, [m], today=TODAY)

    total = sum(r.rate for r in results if r.member_id == "m1")
    assert total == 130.0
