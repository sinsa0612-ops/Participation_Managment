"""사업별 예산 미소진 '사유' 진단 (F17 / Path A — 읽기 전용).

배분 알고리즘은 그대로 두고, 각 사업의 잔여 예산이 왜 남았는지만 설명한다.
- saturated(인력 포화): 사업 기간에 참여 가능한 미배정 연구원이 전부 상한(동시 사업수/월 참여율)에 도달.
- slack(추가 여력): 재배분 시 더 투입할 수 있는 연구원이 있음.
'추가 가능' 판정은 배분 게이트와 동일하게 '전체 참여 가능 기간 내내 여유가 있어야 함' 기준을 쓴다
(distribute가 부분기간 자동 축소 배정을 하지 않으므로).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.services.calc import ROUNDING_UNIT, to_month_idx
from app.services.distribute import (
    MIN_PARTICIPATION_RATE,
    MemberData,
    ProjectData,
    counts_toward_concurrency,
)


@dataclass
class BudgetDiag:
    project_id: str
    project_name: str
    budget: float
    allocated: float
    remaining: float
    reason: str  # ok | no_budget | saturated | slack
    detail: str
    recruitable: list[str] = field(default_factory=list)


def compute_budget_diagnostics(
    projects: list[ProjectData],
    members: list[MemberData],
    participations,
    today: date,
) -> list[BudgetDiag]:
    proj_end = {p.id: p.end_date for p in projects}
    parts = list(participations)

    def member_month_state(member_id: str, member_rank: str, mi: int) -> tuple[int, float]:
        """특정 월의 (카운트 대상 동시참여 수, 참여율 합). 단장은 단기 사업도 카운트."""
        cnt = 0
        rate = 0.0
        for r in parts:
            if r.member_id != member_id:
                continue
            if to_month_idx(r.start_date) <= mi <= to_month_idx(r.end_date):
                rate += r.rate
                if r.project_id in proj_end and counts_toward_concurrency(member_rank, proj_end[r.project_id], today):
                    cnt += 1
        return cnt, rate

    out: list[BudgetDiag] = []
    for p in projects:
        budget = sum(float(v or 0) for v in p.year_budgets.values())
        allocated = sum(r.cost for r in parts if r.project_id == p.id)
        remaining = budget - allocated

        if budget <= 0:
            out.append(
                BudgetDiag(p.id, p.name, budget, allocated, remaining, "no_budget", "예산이 설정되지 않았습니다.")
            )
            continue
        if remaining < ROUNDING_UNIT:
            out.append(
                BudgetDiag(p.id, p.name, budget, allocated, max(0.0, remaining), "ok", "예산이 모두 소진되었습니다.")
            )
            continue

        budgeted_years = [int(y) for y, v in p.year_budgets.items() if float(v or 0) > 0]
        min_by, max_by = min(budgeted_years), max(budgeted_years)
        in_proj = {r.member_id for r in parts if r.project_id == p.id}

        recruitable: list[str] = []
        block_proj = block_rate = considered = 0
        for m in members:
            if m.id in in_proj:
                continue
            # 참여 가능 기간 = 사업기간 ∩ 예산연도 ∩ 재직기간
            s = max(to_month_idx(p.start_date), to_month_idx(f"{min_by}-01-01"))
            e = min(to_month_idx(p.end_date), to_month_idx(f"{max_by}-12-31"))
            if m.hire_date:
                s = max(s, to_month_idx(m.hire_date))
            if m.resign_date:
                e = min(e, to_month_idx(m.resign_date))
            if s > e:
                continue  # 애초에 참여 불가능한 연구원은 사유 집계에서 제외
            considered += 1

            p_counts = counts_toward_concurrency(m.rank, p.end_date, today)
            first_block = None
            for mi in range(s, e + 1):
                cnt, rate = member_month_state(m.id, m.rank, mi)
                if cnt + (1 if p_counts else 0) > m.max_projects:
                    first_block = "proj"
                    break
                if rate + MIN_PARTICIPATION_RATE > m.max_rate + 0.01:
                    first_block = "rate"
                    break
            if first_block is None:
                recruitable.append(m.name)
            elif first_block == "proj":
                block_proj += 1
            else:
                block_rate += 1

        if recruitable:
            out.append(
                BudgetDiag(
                    p.id,
                    p.name,
                    budget,
                    allocated,
                    remaining,
                    "slack",
                    f"재배분 시 추가 투입 가능: {', '.join(recruitable)}",
                    list(recruitable),
                )
            )
        elif considered == 0:
            out.append(
                BudgetDiag(
                    p.id,
                    p.name,
                    budget,
                    allocated,
                    remaining,
                    "saturated",
                    "이 기간에 참여 가능한 미배정 연구원이 없습니다. 인원 추가나 사업 기간 조정이 필요합니다.",
                )
            )
        else:
            cap = "동시 사업수 상한" if block_proj >= block_rate else "월 참여율 상한"
            out.append(
                BudgetDiag(
                    p.id,
                    p.name,
                    budget,
                    allocated,
                    remaining,
                    "saturated",
                    f"참여 가능 연구원 전원이 {cap}에 도달했습니다(인력 포화). 인원 추가나 상한 조정이 필요합니다.",
                )
            )
    return out
