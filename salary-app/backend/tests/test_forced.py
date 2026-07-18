"""강제 참여(member_months)·제외(excluded_members) 배분 동작 테스트 (#3·#4)."""

from __future__ import annotations

from datetime import date

from app.services.distribute import MemberData, ProjectData, auto_distribute

TODAY = date(2025, 1, 1)
FULL_SPAN = ["2025-01", "2026-12"]  # member_months 창: 첫·마지막 값으로 기간 결정


def _director(max_projects=2, max_rate=50):
    return MemberData(
        id="d",
        name="단장",
        employ_type="정규직",
        rank="단장",
        salary=1_000_000,
        max_rate=max_rate,
        max_projects=max_projects,
    )


def _proj(pid, end, *, chief="d", months=None, excluded=None):
    return ProjectData(
        id=pid,
        name=pid,
        start_date="2025-01-01",
        end_date=end,
        year_budgets={"2025": 50_000_000, "2026": 50_000_000},
        required_chief=chief,
        member_months={"d": months} if months else {},
        excluded_members=excluded or [],
    )


def test_forced_months_reserve_slots_blocking_others():
    """단장(2개)을 P1·P3에 강제 참여시키면 두 사업에 반드시 배정되고, 두 슬롯이 다 찬 달에는
    P2가 끼어들 수 없다(#4). 단, P1이 끝난(2026-06) 뒤의 달엔 슬롯이 비므로 P2가 들어갈 수 있다 —
    어느 달에도 동시참여 ≤ max_projects(2)만 지키면 된다(F5, 부분기간 배정)."""
    from app.services.distribute import _to_month_idx

    p1 = _proj("P1", "2026-06-30", months=FULL_SPAN)
    p2 = _proj("P2", "2026-09-30")  # 강제 아님
    p3 = _proj("P3", "2026-12-31", months=FULL_SPAN)
    results = auto_distribute([p1, p2, p3], [_director()], today=TODAY)
    mine = [r for r in results if r.member_id == "d"]
    proj_ids = {r.project_id for r in mine}
    assert {"P1", "P3"} <= proj_ids  # 강제한 두 사업엔 반드시 배정
    # P1·P3가 둘 다 활성인 달(2025-01~2026-06)엔 P2가 끼어들 수 없다(이미 2슬롯 점유)
    for mi in range(_to_month_idx("2025-01-01"), _to_month_idx("2026-06-30") + 1):
        active = {r.project_id for r in mine if _to_month_idx(r.start_date) <= mi <= _to_month_idx(r.end_date)}
        assert "P2" not in active
        assert len(active) <= 2


def test_excluded_member_never_assigned():
    """제외된 연구원은 그 사업에 (필수 참여자여도) 배정되지 않는다(#3)."""
    p = _proj("P", "2026-12-31", excluded=["d"])
    results = auto_distribute([p], [_director(max_projects=5, max_rate=100)], today=TODAY)
    assert not any(r.project_id == "P" and r.member_id == "d" for r in results)


def test_forced_within_caps_total_rate_not_exceeded():
    """강제 2개 배분이어도 월 참여율 합은 상한(50%)을 넘지 않는다."""
    p1 = _proj("P1", "2026-06-30", months=FULL_SPAN)
    p3 = _proj("P3", "2026-12-31", months=FULL_SPAN)
    results = auto_distribute([p1, p3], [_director(max_rate=50)], today=TODAY)
    # 2025년 어느 달이든 두 사업 참여율 합 ≤ 50
    from app.services.distribute import _to_month_idx

    mine = [r for r in results if r.member_id == "d"]
    for mi in range(_to_month_idx("2025-01-01"), _to_month_idx("2026-12-01") + 1):
        s = sum(r.rate for r in mine if _to_month_idx(r.start_date) <= mi <= _to_month_idx(r.end_date))
        assert s <= 50.01
