"""사업 예산 소진 우선순위(sort_order) 테스트 (#2).

sort_order가 작을수록 먼저 인력을 확보(예산을 먼저 채움)한다. 미설정(0)이면 기존 정렬(종료일·예산)로 폴백.
"""

from __future__ import annotations

from datetime import date

from app.services.distribute import MemberData, ProjectData, auto_distribute

TODAY = date(2025, 1, 1)


def _member():
    return MemberData(
        id="m", name="M", employ_type="정규직", rank="연구원", salary=1_000_000, max_rate=100, max_projects=1
    )


def test_sort_order_controls_fill_priority():
    """단일 슬롯(max_projects=1)을 두 장기 사업이 경합 → sort_order 낮은 쪽이 가져간다."""
    early = ProjectData(
        id="early",
        name="조기종료",
        start_date="2025-01-01",
        end_date="2026-06-30",
        year_budgets={"2025": 30_000_000, "2026": 30_000_000},
        required_chief="m",
        sort_order=1,
    )
    late = ProjectData(
        id="late",
        name="후순위지만우선",
        start_date="2025-01-01",
        end_date="2026-12-31",
        year_budgets={"2025": 30_000_000, "2026": 30_000_000},
        required_chief="m",
        sort_order=0,
    )
    results = auto_distribute([early, late], [_member()], today=TODAY)
    proj_ids = {r.project_id for r in results if r.member_id == "m"}
    assert proj_ids == {"late"}  # sort_order=0이 슬롯 선점


def test_default_sort_order_falls_back_to_end_date():
    """sort_order가 같으면(기본 0) 종료일 빠른 사업이 슬롯을 먼저 가져간다.

    early(2026-06 종료)가 먼저 인력을 통째로 확보하고, late는 early가 끝난 뒤
    겹치지 않는 달(2026-07~)에만 남은 용량을 받는다. 어느 달에도 동시참여 ≤ max_projects(1).
    """
    from app.services.distribute import _to_month_idx

    early = ProjectData(
        id="early",
        name="조기종료",
        start_date="2025-01-01",
        end_date="2026-06-30",
        year_budgets={"2025": 30_000_000, "2026": 30_000_000},
        required_chief="m",
    )
    late = ProjectData(
        id="late",
        name="후종료",
        start_date="2025-01-01",
        end_date="2026-12-31",
        year_budgets={"2025": 30_000_000, "2026": 30_000_000},
        required_chief="m",
    )
    results = auto_distribute([early, late], [_member()], today=TODAY)
    mine = [r for r in results if r.member_id == "m"]
    # early가 슬롯을 선점: early 전 기간(2025-01~2026-06) 내내 m이 배정됨
    early_months = {
        mi
        for r in mine
        if r.project_id == "early"
        for mi in range(_to_month_idx(r.start_date), _to_month_idx(r.end_date) + 1)
    }
    assert early_months == set(range(_to_month_idx("2025-01-01"), _to_month_idx("2026-06-30") + 1))
    # late는 early와 겹치는 달엔 못 들어감 → late 배정은 모두 2026-07 이후
    for r in mine:
        if r.project_id == "late":
            assert _to_month_idx(r.start_date) > _to_month_idx("2026-06-30")
    # 월별 동시참여 ≤ 1
    for mi in range(_to_month_idx("2025-01-01"), _to_month_idx("2026-12-01") + 1):
        concurrent = {r.project_id for r in mine if _to_month_idx(r.start_date) <= mi <= _to_month_idx(r.end_date)}
        assert len(concurrent) <= 1
