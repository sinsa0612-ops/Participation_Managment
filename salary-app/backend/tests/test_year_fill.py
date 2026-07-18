"""연도별 세그먼트 배분 — 다년도 사업 예산을 끝까지(<1000원) 소진하는지 검증.

핵심 동작 변경: 한 (사업, 연구원) 참여를 '전 기간 단일 참여율'이 아니라 '연도·연속가용구간별 세그먼트'로
쪼개, 한 연도/기간이 포화돼도 다른 연도/기간 예산을 독립적으로 소진한다.
"""

from __future__ import annotations

from datetime import date

from app.services.distribute import MemberData, ProjectData, auto_distribute, _to_month_idx

TODAY = date(2025, 1, 1)


def _m(mid, salary=1_000_000, max_rate=100, max_projects=5):
    return MemberData(
        id=mid, name=mid, employ_type="정규직", rank="연구원", salary=salary, max_rate=max_rate, max_projects=max_projects
    )


def _year_cost(results, pid, year):
    """사업의 해당 연도 배정액. 같은 참여율의 다년 세그먼트가 한 행으로 병합될 수 있어,
    세그먼트 비용을 그 연도에 걸친 개월 비율로 안분한다(월별 비용이 균일하므로 정확)."""
    ys, ye = _to_month_idx(f"{year}-01-01"), _to_month_idx(f"{year}-12-31")
    total = 0.0
    for r in results:
        if r.project_id != pid:
            continue
        s, e = _to_month_idx(r.start_date), _to_month_idx(r.end_date)
        months = e - s + 1
        in_year = max(0, min(e, ye) - max(s, ys) + 1)
        if in_year:
            total += r.cost * in_year / months
    return total


def test_multiyear_high_priority_fully_consumed():
    """다년도 사업 + 충분한 인력 → 연도별 예산이 1000원 미만으로 소진된다."""
    members = [_m(f"m{i}") for i in range(4)]  # 4명 × 100% × 12개월 × 1M = 48M/년 용량
    p = ProjectData(
        id="p", name="p", start_date="2025-01-01", end_date="2026-12-31",
        year_budgets={"2025": 30_000_000, "2026": 30_000_000}, sort_order=0,
    )
    res = auto_distribute([p], members, today=TODAY)
    assert 30_000_000 - _year_cost(res, "p", 2025) < 1000
    assert 30_000_000 - _year_cost(res, "p", 2026) < 1000


def test_year_decoupling_saturated_year_does_not_block_other():
    """2025 예산이 작아 50%에서 포화돼도, 2026 예산은 100%까지 독립 소진된다(원래 버그).

    단일 참여율이면 2025(50%)에 묶여 2026은 절반만 채워졌다. 연도 세그먼트로 분리되어
    2025=50%, 2026=100% 의 서로 다른 참여율을 갖는다.
    """
    a = _m("a")  # 1M, 100%
    p = ProjectData(
        id="p", name="p", start_date="2025-01-01", end_date="2026-12-31",
        year_budgets={"2025": 6_000_000, "2026": 12_000_000}, required_chief="a", sort_order=0,
    )
    res = auto_distribute([p], [a], today=TODAY)
    segs = sorted((r for r in res if r.member_id == "a"), key=lambda r: r.start_date)
    assert len(segs) == 2  # 2025·2026 두 세그먼트
    assert segs[0].start_date.startswith("2025") and abs(segs[0].rate - 50) < 0.01
    assert segs[1].start_date.startswith("2026") and abs(segs[1].rate - 100) < 0.01
    assert 6_000_000 - _year_cost(res, "p", 2025) < 1000
    assert 12_000_000 - _year_cost(res, "p", 2026) < 1000


def test_intra_year_window_recovery():
    """상위 사업으로 상반기가 꽉 찬 연구원이, 그 사업이 끝난 하반기엔 하위 사업에 투입된다.

    전 기간 단일 세그먼트면 상반기 막힘이 하반기까지 통째로 차단해 하위 사업 용량이 잔류한다.
    연속 가용 구간(window) 배정으로 하반기를 살려 쓴다.
    """
    a = _m("a")
    high = ProjectData(
        id="high", name="상반기상위", start_date="2025-01-01", end_date="2025-06-30",
        year_budgets={"2025": 6_000_000}, required_chief="a", sort_order=0,  # a 100%×6개월=6M 소진
    )
    low = ProjectData(
        id="low", name="연간하위", start_date="2025-01-01", end_date="2025-12-31",
        year_budgets={"2025": 12_000_000}, sort_order=1,  # a는 일반참여자 — high가 끝난 하반기에만 투입
    )
    res = auto_distribute([high, low], [a], today=TODAY)
    low_segs = [r for r in res if r.project_id == "low" and r.member_id == "a"]
    assert low_segs, "하위 사업이 하반기 가용분을 받아야 한다"
    # low 참여는 high가 끝난 7월 이후에만 시작
    assert all(_to_month_idx(r.start_date) >= _to_month_idx("2025-07-01") for r in low_segs)
    # 월별 참여율 합 ≤ 100 (동시 상한)
    for mi in range(_to_month_idx("2025-01-01"), _to_month_idx("2025-12-01") + 1):
        s = sum(r.rate for r in res if r.member_id == "a" and _to_month_idx(r.start_date) <= mi <= _to_month_idx(r.end_date))
        assert s <= 100.01
