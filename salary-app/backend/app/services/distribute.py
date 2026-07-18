"""
autoDistribute 알고리즘 — TypeScript 프로토타입 → Python 이식

원본: docs/salary_distribution.tsx > autoDistribute()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from math import floor

from app.config import settings
from app.ids import new_id

# 인건비/기간 계산은 SSOT인 calc 모듈에 위임한다. (기존 호출부 호환을 위해 별칭 유지)
# _clamp_months 는 이 모듈에선 더 안 쓰지만 라우터·특성화 테스트가 distribute 경유로 import 하므로 재노출 유지.
from app.services.calc import (
    ROUNDING_UNIT,
    clamp_months as _clamp_months,  # noqa: F401  (router/tests 재노출용)
    month_idx_to_first_day as _month_idx_to_first_day,
    month_idx_to_last_day as _month_idx_to_last_day,
    round_down_to_unit,
    to_month_idx as _to_month_idx,
)

# 배분 규칙 상수 (매직넘버 제거)
MIN_PARTICIPATION_RATE = 10  # 배정 시 최소 참여율(%)
COUNTABLE_MIN_MONTHS = 6  # 동시참여 카운트에 포함되는 사업의 최소 잔여 개월
DIRECTOR_RANK = "단장"  # 동시 참여 사업수 상한을 단기 사업까지 포함해 하드 강제하는 직급
MAX_CHIEF_PROJECTS = 3  # '주관 사업 연구책임자'로서 동시 수행 상한 — 3책(#5, 혁신법 시행령 제64조)
NAT_FUNDING = "정부수탁"  # 국가과제 재원 — 합산 월 100% 상한 대상(#6)


# ──────────────────────────────────────────
# 날짜 유틸
# ──────────────────────────────────────────


def _months_to_end(end_date: str, today: date) -> int:
    """기준일(today) 기준으로 종료일까지 남은 개월 수"""
    e = date.fromisoformat(end_date)
    return (e.year - today.year) * 12 + (e.month - today.month)


def is_project_countable(end_date: str, today: date) -> bool:
    """동시 참여 사업 수 카운트 대상 여부 (F5).

    종료가 COUNTABLE_MIN_MONTHS개월 미만 남은 사업은 '동시참여 수' 계산에서 제외한다.
    => 참여가 6개여도 그중 종료 임박 사업이 있으면 더 적게 센다(사용자 확정 규칙).
    배분 게이트와 참여현황 통계가 이 단일 규칙을 공유한다.
    """
    return _months_to_end(end_date, today) >= COUNTABLE_MIN_MONTHS


def counts_toward_concurrency(member_rank: str, project_end_date: str, today: date) -> bool:
    """이 사업이 해당 연구원의 '동시 참여 사업 수'에 잡히는가 (#1).

    단장은 단기 사업까지 전부 카운트해 max_projects를 하드 강제한다.
    그 외 직급은 잔여 COUNTABLE_MIN_MONTHS개월 미만 사업을 제외하는 기존 규칙을 따른다.
    """
    if member_rank == DIRECTOR_RANK:
        return True
    return is_project_countable(project_end_date, today)


def _total_budget(year_budgets: dict) -> float:
    return sum(float(v or 0) for v in year_budgets.values())


# ──────────────────────────────────────────
# 내부 데이터 클래스 (DB 모델과 독립적)
# ──────────────────────────────────────────


@dataclass
class MemberData:
    id: str
    name: str
    employ_type: str
    rank: str
    salary: float
    max_rate: float = 100.0
    max_projects: int = 5
    hire_date: str | None = None
    resign_date: str | None = None


@dataclass
class ProjectData:
    id: str
    name: str
    start_date: str
    end_date: str
    year_budgets: dict = field(default_factory=dict)  # {year: total_amount} — 연도별 총액(고용형태 구분 없음, F4)
    required_chief: str | None = None
    required_staff: list[str] = field(default_factory=list)
    member_constraints: dict[str, float] = field(default_factory=dict)  # {member_id: max_rate}
    member_months: dict[str, list[str]] = field(default_factory=dict)  # {member_id: ["YYYY-MM", ...]}
    sort_order: int = 0  # 예산 소진 우선순위 — 작을수록 먼저 인력 확보(#2)
    excluded_members: list[str] = field(default_factory=list)  # 이 사업에서 배제할 연구원(#3)
    org_role: str = "주관"  # 주관 | 참여 — 주관 사업 연구책임자만 3책 카운트(#5)
    funding_source: str = NAT_FUNDING  # 정부수탁 | 기본사업 — 재원별 참여율 상한(#6)


@dataclass
class AllocationRecord:
    project_id: str
    start_date: str
    end_date: str
    rate: float


@dataclass
class ParticipationResult:
    id: str
    project_id: str
    member_id: str
    role: str
    start_date: str
    end_date: str
    rate: float
    cost: float


# ──────────────────────────────────────────
# 제약/상태 조회 헬퍼 (member_allocs = 연구원별 현재 배분 상태)
# ──────────────────────────────────────────


def _countable_projects_at(
    member_allocs: dict[str, list[AllocationRecord]],
    projects: list[ProjectData],
    member_id: str,
    month_idx: int,
    current_project_id: str,
    today: date,
    member_rank: str = "",
) -> int:
    """특정 월에 동시 참여 중인 '카운트 대상' 사업 수 (현재 사업 제외).

    일반 직급은 잔여 6개월 미만 사업을 제외하지만, 단장은 전부 카운트한다(member_rank로 분기).
    한 사업이 연도별 세그먼트로 여러 alloc을 가져도 '사업 수'로는 1개만 센다(project_id 중복 제거).
    """
    seen: set[str] = set()
    for a in member_allocs[member_id]:
        if a.project_id == current_project_id or a.project_id in seen:
            continue
        if not (_to_month_idx(a.start_date) <= month_idx <= _to_month_idx(a.end_date)):
            continue
        proj = next((p for p in projects if p.id == a.project_id), None)
        if not proj:
            continue
        if counts_toward_concurrency(member_rank, proj.end_date, today):
            seen.add(a.project_id)
    return len(seen)


def _concurrent_rate_at(
    member_allocs: dict[str, list[AllocationRecord]],
    member_id: str,
    month_idx: int,
    current_project_id: str,
    only_project_ids: set[str] | None = None,
) -> float:
    """특정 월의 참여율 합계 (현재 사업 제외). only_project_ids로 재원별(정부수탁만 등) 합산 가능(#6)."""
    return sum(
        a.rate
        for a in member_allocs[member_id]
        if a.project_id != current_project_id
        and (only_project_ids is None or a.project_id in only_project_ids)
        and _to_month_idx(a.start_date) <= month_idx <= _to_month_idx(a.end_date)
    )


def _chief_projects_at(
    member_allocs: dict[str, list[AllocationRecord]],
    projects: list[ProjectData],
    member_id: str,
    month_idx: int,
    current_project_id: str,
    today: date,
    member_rank: str = "",
) -> int:
    """특정 월에 '주관 사업의 연구책임자'로 동시 수행 중인 사업 수 (현재 사업 제외) — 3책(#5).

    참여기관(org_role="참여") 사업의 책임자는 공동연구책임자에 해당해 카운트하지 않는다.
    과제 수 산정 제외 규칙(잔여 6개월 미만·단장 예외)은 5공 카운트와 동일하게 공유한다.
    """
    seen: set[str] = set()
    for a in member_allocs[member_id]:
        if a.project_id == current_project_id or a.project_id in seen:
            continue
        if not (_to_month_idx(a.start_date) <= month_idx <= _to_month_idx(a.end_date)):
            continue
        proj = next((p for p in projects if p.id == a.project_id), None)
        if not proj or proj.org_role != "주관" or proj.required_chief != member_id:
            continue
        if counts_toward_concurrency(member_rank, proj.end_date, today):
            seen.add(a.project_id)
    return len(seen)


def _month_avail(
    member: MemberData,
    proj: ProjectData,
    month_idx: int,
    member_allocs: dict[str, list[AllocationRecord]],
    nat_ids: set[str],
) -> float:
    """이 (사업, 연구원, 월)에 추가 계상 가능한 참여율 여유 (현재 사업 제외, 재원별 상한 반영, #6).

    - 전체(기본사업 포함) 합산 ≤ settings.total_rate_cap (비영리 130% 특례)
    - 정부수탁 사업이면 추가로: 정부수탁 합산 ≤ min(개인 국비 상한 max_rate, settings.nat_rate_cap)
    member.max_rate는 '국비 참여율 상한'이므로 기본사업에는 적용하지 않는다.
    사업별 개인 상한(member_constraints)은 호출부에서 별도로 min 조합한다.
    """
    used_total = _concurrent_rate_at(member_allocs, member.id, month_idx, proj.id)
    avail = settings.total_rate_cap - used_total
    if proj.funding_source == NAT_FUNDING:
        used_nat = _concurrent_rate_at(member_allocs, member.id, month_idx, proj.id, nat_ids)
        avail = min(avail, min(member.max_rate, settings.nat_rate_cap) - used_nat)
    return avail


# ──────────────────────────────────────────
# 알고리즘
# ──────────────────────────────────────────


def _priority_ids(proj: ProjectData) -> list[str]:
    ids = list(
        dict.fromkeys([proj.required_chief] + proj.required_staff if proj.required_chief else proj.required_staff)
    )
    return [mid for mid in ids if mid]


def _result_year(r: ParticipationResult) -> int:
    """세그먼트는 한 연도 안에 있으므로 시작일의 연도가 그 세그먼트의 예산 연도다."""
    return int(r.start_date[:4])


def _budget_years(proj: ProjectData) -> list[int]:
    """예산이 있고 사업 기간과 겹치는 연도 목록 (오름차순)."""
    years = sorted(int(y) for y, v in proj.year_budgets.items() if float(v or 0) > 0)
    ps, pe = _to_month_idx(proj.start_date), _to_month_idx(proj.end_date)
    return [y for y in years if _to_month_idx(f"{y}-01-01") <= pe and _to_month_idx(f"{y}-12-31") >= ps]


def _segment_bounds(proj: ProjectData, member: MemberData, year: int) -> tuple[int, int] | None:
    """(사업, 연도)에서 member 참여 가능 기간의 월 인덱스 (start_mi, end_mi) 또는 None.

    기간 우선순위: member_months(강제 월의 전체 span) > 재직기간 > 사업 전체.
    그 기간을 (사업기간 ∩ 해당 연도)로 클리핑한다.
    """
    all_ym = sorted(proj.member_months.get(member.id, []))
    if all_ym:
        base_start_m = _to_month_idx(all_ym[0] + "-01")
        base_end_m = _to_month_idx(all_ym[-1] + "-01")
    else:
        base_start_m = _to_month_idx(proj.start_date)
        base_end_m = _to_month_idx(proj.end_date)

    start_m = max(base_start_m, _to_month_idx(proj.start_date), _to_month_idx(f"{year}-01-01"))
    end_m = min(base_end_m, _to_month_idx(proj.end_date), _to_month_idx(f"{year}-12-31"))
    if member.hire_date:
        start_m = max(start_m, _to_month_idx(member.hire_date))
    if member.resign_date:
        end_m = min(end_m, _to_month_idx(member.resign_date))
    if start_m > end_m:
        return None
    return start_m, end_m


def _assign_segment(
    proj: ProjectData,
    member: MemberData,
    year: int,
    member_allocs: dict[str, list[AllocationRecord]],
    projects: list[ProjectData],
    proj_year_remain: dict[tuple[str, int], float],
    today: date,
    results: list[ParticipationResult],
    nat_ids: set[str],
) -> bool:
    """(사업, 연구원, 연도)에서 member가 참여 가능한 '최대 연속 가용 구간'마다 세그먼트를 10%로 배정.

    한 연도 안에서도 월별 동시참여 여유는 달라진다(예: 상반기는 다른 사업으로 꽉 차고 하반기엔 빔).
    전 구간을 한 세그먼트로 묶으면 막힌 달 하나가 빈 달까지 통째로 차단해 용량이 잔류한다.
    => 가용한 달들의 '연속 구간(window)'마다 따로 세그먼트를 만들어, 비는 기간을 끝까지 활용한다.

    하나 이상 배정되면 True. 0차(강제)·A차(필수)·B차(일반) 모든 패스가 이 로직을 공유한다.
    """
    bounds = _segment_bounds(proj, member, year)
    if bounds is None:
        return False
    base_start, base_end = bounds

    constraint_rate = proj.member_constraints.get(member.id)
    # 이 배정이 '주관 사업의 연구책임자' 자리인가 — 그렇다면 3책 게이트 적용(#5)
    is_lead_chief = proj.org_role == "주관" and member.id == proj.required_chief

    # 추가 가능한 달들을 '가용 여유가 같은' 연속 구간(window)으로 묶는다.
    #   단순 가용/불가뿐 아니라 '여유 참여율'이 바뀌는 지점에서도 끊는다 — 한 세그먼트는 단일 참여율이라,
    #   여유가 다른 달을 한데 묶으면 가장 빡빡한 달이 전체를 눌러 빈 여유가 잔류하기 때문(현재 사업 제외).
    windows: list[tuple[int, int]] = []
    run_start: int | None = None
    run_avail: float | None = None
    for mi in range(base_start, base_end + 1):
        cnt = _countable_projects_at(member_allocs, projects, member.id, mi, proj.id, today, member.rank)
        avail = _month_avail(member, proj, mi, member_allocs, nat_ids)
        if constraint_rate is not None:
            avail = min(avail, constraint_rate)
        chief_ok = not is_lead_chief or (
            _chief_projects_at(member_allocs, projects, member.id, mi, proj.id, today, member.rank)
            < MAX_CHIEF_PROJECTS
        )
        addable = cnt < member.max_projects and chief_ok and avail >= MIN_PARTICIPATION_RATE
        avail_key = round(avail, 2) if addable else None
        if avail_key != run_avail:
            if run_start is not None:
                windows.append((run_start, mi - 1))
            run_start = mi if addable else None
            run_avail = avail_key
    if run_start is not None:
        windows.append((run_start, base_end))

    role = (
        "연구책임자"
        if member.id == proj.required_chief
        else "실무자"
        if member.id in proj.required_staff
        else "일반참여자"
    )
    key = (proj.id, year)
    created = False
    for s_mi, e_mi in windows:
        remain = proj_year_remain[key]
        mon = e_mi - s_mi + 1
        min_cost = round_down_to_unit(member.salary * mon * MIN_PARTICIPATION_RATE / 100)
        if min_cost <= 0 or min_cost > remain:
            continue
        seg_start = _month_idx_to_first_day(s_mi)
        seg_end = _month_idx_to_last_day(e_mi)
        results.append(
            ParticipationResult(
                id=new_id(),
                project_id=proj.id,
                member_id=member.id,
                role=role,
                start_date=seg_start,
                end_date=seg_end,
                rate=float(MIN_PARTICIPATION_RATE),
                cost=float(min_cost),
            )
        )
        member_allocs[member.id].append(
            AllocationRecord(
                project_id=proj.id, start_date=seg_start, end_date=seg_end, rate=float(MIN_PARTICIPATION_RATE)
            )
        )
        proj_year_remain[key] = remain - min_cost
        created = True
    return created


def _fill_year(
    proj: ProjectData,
    year: int,
    member_map: dict[str, MemberData],
    member_allocs: dict[str, list[AllocationRecord]],
    proj_year_remain: dict[tuple[str, int], float],
    results: list[ParticipationResult],
    nat_ids: set[str],
) -> None:
    """(사업, 연도) 한 연도의 잔액을 그 연도 세그먼트들의 참여율을 올려 소진한다.

    연도가 독립이므로(세그먼트가 한 연도 안에 갇힘) 한 연도가 포화돼도 다른 연도를 막지 않는다.
    => 이것이 다년도 사업이 전 기간 단일 참여율로는 못 채우던 잔액을 끝까지 소진하는 핵심이다.
    """
    key = (proj.id, year)
    remain = proj_year_remain[key]
    if remain < ROUNDING_UNIT:
        return

    seg_results = [r for r in results if r.project_id == proj.id and _result_year(r) == year]
    for r in seg_results:
        if remain < ROUNDING_UNIT:
            break
        member = member_map.get(r.member_id)
        if not member:
            continue

        s_mi, e_mi = _to_month_idx(r.start_date), _to_month_idx(r.end_date)
        mon = e_mi - s_mi + 1
        if mon <= 0:
            continue
        salary_per_pct = member.salary * mon / 100
        if salary_per_pct <= 0:
            continue

        constraint_rate = proj.member_constraints.get(r.member_id)
        # 재원별 개인 상한(#6): 정부수탁은 국비 상한(max_rate), 기본사업은 전체 상한만 적용
        personal_cap = (
            min(member.max_rate, settings.nat_rate_cap)
            if proj.funding_source == NAT_FUNDING
            else settings.total_rate_cap
        )
        member_max_rate = min(constraint_rate, personal_cap) if constraint_rate is not None else personal_cap

        # 월별 동시참여 여유 = min(개인·재원 상한, 그 달의 재원별 잔여 여유)
        min_avail_rate = member_max_rate
        for mi in range(s_mi, e_mi + 1):
            min_avail_rate = min(min_avail_rate, _month_avail(member, proj, mi, member_allocs, nat_ids))

        max_additional = min_avail_rate - r.rate
        if max_additional <= 0:
            continue

        budget_additional = (remain / (member.salary * mon)) * 100
        additional_rate = min(max_additional, budget_additional)

        # 표시 참여율을 소수 2자리로 '내림' 확정한 뒤, 인건비는 확정된 참여율 기준으로 계산한다.
        #   이전에는 반올림 전 rate로 인건비를 계산해 '저장된 참여율 × 급여'보다 큰 금액이
        #   계상될 수 있었다(최대 ~1천원) — 독립 검증기(#7)가 발견한 정합성 결함.
        #   내림이므로 월 참여율 상한도 절대 넘지 않는다.
        new_rate = floor((r.rate + additional_rate) * 100 + 1e-9) / 100
        additional_rate_floored = new_rate - r.rate
        if additional_rate_floored <= 0:
            continue

        additional_cost = round_down_to_unit(member.salary * mon * additional_rate_floored / 100)
        if additional_cost <= 0 or additional_cost > remain:
            continue

        alloc = next(
            (a for a in member_allocs[r.member_id] if a.project_id == proj.id and a.start_date == r.start_date), None
        )
        if alloc:
            alloc.rate = new_rate
        r.rate = new_rate
        r.cost += additional_cost
        remain -= additional_cost

    proj_year_remain[key] = remain


def auto_distribute(
    projects: list[ProjectData],
    members: list[MemberData],
    today: date | None = None,
) -> list[ParticipationResult]:
    if today is None:
        today = settings.base_date
    results: list[ParticipationResult] = []

    # 사업 정렬: 우선순위(작을수록 먼저) → 종료일 빠른 순 → 예산 큰 순
    sorted_projs = sorted(projects, key=lambda p: (p.sort_order, p.end_date, -_total_budget(p.year_budgets)))

    # 연구원별 현재 배분(세그먼트) 추적
    member_allocs: dict[str, list[AllocationRecord]] = {m.id: [] for m in members}
    member_map = {m.id: m for m in members}

    # 정부수탁 사업 id — 재원별 상한(국비 100% / 전체 130%) 합산용(#6)
    nat_ids = {p.id for p in projects if p.funding_source == NAT_FUNDING}

    # (사업, 연도)별 잔여 예산 — 연도를 독립적으로 채운다.
    proj_year_remain: dict[tuple[str, int], float] = {}
    proj_years: dict[str, list[int]] = {}
    for proj in sorted_projs:
        if not proj.start_date or not proj.end_date:
            continue
        years = _budget_years(proj)
        if not years:
            continue
        proj_years[proj.id] = years
        for y in years:
            proj_year_remain[(proj.id, y)] = float(proj.year_budgets.get(str(y), 0) or 0)

    def assigned_in(pid: str, year: int) -> set[str]:
        return {r.member_id for r in results if r.project_id == pid and _result_year(r) == year}

    # 0차 패스: 강제 참여(member_months)를 모든 사업·연도에 먼저 예약 — 슬롯 선점 (#4)
    for proj in sorted_projs:
        for year in proj_years.get(proj.id, []):
            here = assigned_in(proj.id, year)
            forced_priority = [mid for mid in _priority_ids(proj) if mid in proj.member_months]
            forced_other = [mid for mid in proj.member_months if mid not in forced_priority]
            for member_id in forced_priority + forced_other:
                if member_id in proj.excluded_members or member_id in here:
                    continue
                member = member_map.get(member_id)
                if member and _assign_segment(
                    proj, member, year, member_allocs, projects, proj_year_remain, today, results, nat_ids
                ):
                    here.add(member_id)

    # A차 패스: 필수 인원(연구책임자/실무자)을 모든 사업·연도에 10% 예약 — 하위 사업도 필수는 보장
    for proj in sorted_projs:
        for year in proj_years.get(proj.id, []):
            here = assigned_in(proj.id, year)
            for member_id in _priority_ids(proj):
                if member_id in here or member_id in proj.excluded_members:
                    continue
                member = member_map.get(member_id)
                if member and _assign_segment(
                    proj, member, year, member_allocs, projects, proj_year_remain, today, results, nat_ids
                ):
                    here.add(member_id)

    # B차 패스: 우선순위 순으로 사업을, 그 안에서 연도별로 '예산까지' 채운다 (하드 순차 채움).
    #   각 (사업, 연도)에서 일반 참여자 투입 + 즉시 증액을 끝낸 뒤 다음으로 → 1순위가 연도별 인력을 먼저 가져가고
    #   하위 사업은 남은 만큼만. 연도가 독립이라 한 연도 포화가 다른 연도 소진을 막지 않는다.
    for proj in sorted_projs:
        for year in proj_years.get(proj.id, []):
            key = (proj.id, year)
            here = assigned_in(proj.id, year)
            for member_id in [m.id for m in members]:
                if proj_year_remain[key] <= 0:
                    break
                if member_id in here or member_id in proj.excluded_members:
                    continue
                member = member_map.get(member_id)
                if member and _assign_segment(
                    proj, member, year, member_allocs, projects, proj_year_remain, today, results, nat_ids
                ):
                    here.add(member_id)
            _fill_year(proj, year, member_map, member_allocs, proj_year_remain, results, nat_ids)

    return _merge_adjacent_segments(results)


def _merge_adjacent_segments(results: list[ParticipationResult]) -> list[ParticipationResult]:
    """같은 (연구원, 사업)에서 참여율이 같고 기간이 맞닿은 세그먼트를 하나로 합친다(출력 정리).

    연도·가용여유로 잘게 쪼개졌어도 결과 참여율이 같으면 굳이 행을 나눌 필요가 없다.
    소진 총액·월별 참여율은 그대로 두고 표시 행 수만 줄인다(인건비는 천원 단위 합이라 불변식 유지).
    """
    by_mp: dict[tuple[str, str], list[ParticipationResult]] = {}
    for r in results:
        by_mp.setdefault((r.member_id, r.project_id), []).append(r)

    merged: list[ParticipationResult] = []
    for segs in by_mp.values():
        segs.sort(key=lambda r: r.start_date)
        cur = segs[0]
        for nxt in segs[1:]:
            adjacent = _to_month_idx(nxt.start_date) == _to_month_idx(cur.end_date) + 1
            if adjacent and abs(nxt.rate - cur.rate) < 1e-9:
                cur.end_date = nxt.end_date
                cur.cost += nxt.cost
            else:
                merged.append(cur)
                cur = nxt
        merged.append(cur)
    return merged
