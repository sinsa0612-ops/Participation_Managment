"""연구원별 참여 통계 측정 단위 테스트 (Phase 1).

핵심 회귀 방지 대상:
- 참여율 '합계'는 안 겹치는 달까지 더한 단순합이 아니라 '그 달의 동시 참여율 합(월별 피크)'이어야 한다.
- 최대 동시참여 사업수는 잔여 6개월 미만 사업을 제외한 '카운트 대상' 동시참여 기준이어야 한다.
  (사용자 확정 규칙: 참여 6개여도 1개가 종료 6개월 미만이면 5개로 본다.)

순수 함수 compute_member_stats를 DB 없이 결정적 기준일로 검증한다.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.services.stats import compute_member_stats

TODAY = date(2025, 1, 1)


def _m(mid, *, max_rate=100.0, max_projects=5, salary=3_000_000):
    return SimpleNamespace(
        id=mid,
        name=mid,
        employ_type="정규직",
        rank="연구원",
        salary=salary,
        max_rate=max_rate,
        max_projects=max_projects,
    )


def _p(pid, end_date):
    return SimpleNamespace(id=pid, end_date=end_date)


def _part(member_id, project_id, start_date, end_date, rate, cost=0.0):
    return SimpleNamespace(
        member_id=member_id,
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        rate=rate,
        cost=cost,
    )


def _only(members, parts, projects):
    return compute_member_stats(members, parts, projects, TODAY)[0]


def test_total_rate_is_monthly_peak_not_naive_sum():
    """안 겹치는 3개 사업(각 40%) → 단순합 120%가 아니라 월 피크 40%로 측정, 상태 정상."""
    members = [_m("a", max_rate=100)]
    projects = [_p("p1", "2025-04-30"), _p("p2", "2025-08-31"), _p("p3", "2025-12-31")]
    parts = [
        _part("a", "p1", "2025-01-01", "2025-04-30", 40),
        _part("a", "p2", "2025-05-01", "2025-08-31", 40),
        _part("a", "p3", "2025-09-01", "2025-12-31", 40),
    ]
    s = _only(members, parts, projects)
    assert s.total_rate == 40  # 월별 피크 (단순합이면 120)
    assert s.status == "정상"  # 단순합 기준이면 잘못 '초과'로 떴음


def test_short_project_excluded_from_concurrent_count():
    """6개 동시 참여지만 1개가 잔여 6개월 미만 → 카운트 대상 5개 → 상한 5 이내, 정상."""
    members = [_m("a", max_projects=5)]
    # 5개는 장기(2025-12-31 종료, today 기준 11개월 → 카운트), 1개는 단기(2025-06-30 종료, 5개월 → 제외)
    projects = [_p(f"p{i}", "2025-12-31") for i in range(5)] + [_p("short", "2025-06-30")]
    parts = [_part("a", f"p{i}", "2025-01-01", "2025-12-31", 10) for i in range(5)]
    parts.append(_part("a", "short", "2025-01-01", "2025-06-30", 10))  # 6월에 6개 겹침
    s = _only(members, parts, projects)
    assert s.proj_count == 6  # 생애 참여 사업수는 6
    assert s.max_concurrent == 5  # 카운트 대상 동시참여는 5
    assert s.status == "정상"  # 6개 겹쳐도 단기 1개 제외하면 상한 이내


def test_over_projects_when_all_countable():
    """6개 동시 참여 + 전부 장기(카운트 대상) → 상한 5 초과."""
    members = [_m("a", max_projects=5)]
    projects = [_p(f"p{i}", "2026-12-31") for i in range(6)]
    parts = [_part("a", f"p{i}", "2025-01-01", "2025-12-31", 10) for i in range(6)]
    s = _only(members, parts, projects)
    assert s.max_concurrent == 6
    assert s.status == "초과"


def test_over_rate_when_monthly_peak_exceeds_cap():
    """같은 달 60%+60% = 120% > 상한 100% → 초과."""
    members = [_m("a", max_rate=100)]
    projects = [_p("p1", "2026-12-31"), _p("p2", "2026-12-31")]
    parts = [
        _part("a", "p1", "2025-01-01", "2025-12-31", 60),
        _part("a", "p2", "2025-01-01", "2025-12-31", 60),
    ]
    s = _only(members, parts, projects)
    assert s.total_rate == 120
    assert s.status == "초과"


def test_unassigned_member():
    members = [_m("a")]
    s = compute_member_stats(members, [], [], TODAY)[0]
    assert s.proj_count == 0
    assert s.max_concurrent == 0
    assert s.total_rate == 0
    assert s.status == "미배분"
