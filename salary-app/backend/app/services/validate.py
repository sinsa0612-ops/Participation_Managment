"""배분 결과 독립 검증기(auditor) — 이중장부 원리(#7).

배분 알고리즘(distribute.py)이 스스로 규칙을 지켰다고 믿는 대신, 최종 결과만 받아
'별개의 단순한 코드'로 전 규칙을 재검사한다. 알고리즘의 가용량 헬퍼(_month_avail 등)를
재사용하지 않는다 — 같은 코드를 쓰면 같은 버그를 공유해 검증이 무의미해지기 때문이다.
(counts_toward_concurrency 같은 '규칙 정의' 상수·판정만 단일 출처로 공유한다.)

검사 항목:
  세그먼트 — 사업기간·재직기간 준수, 최소 참여율 10%, 천원 단위, 초과 계상, 기간 역전
  월별     — 정부수탁 합산 ≤ min(개인 국비 상한, 100%), 전체 합산 ≤ 130%, 5공, 3책(주관 책임자)
  예산     — 사업 총액 ≤ 총예산(정확), 연도별 배분액 ≤ 연도 예산(반올림 허용오차)

수동 조정(override)으로 생긴 위반도 그대로 보고한다 — 사용자가 의도했더라도 규정 위반 사실은 알아야 한다.
"""

from __future__ import annotations

from datetime import date

from app.config import settings
from app.services.calc import ROUNDING_UNIT, to_month_idx
from app.services.distribute import (
    MAX_CHIEF_PROJECTS,
    MIN_PARTICIPATION_RATE,
    NAT_FUNDING,
    MemberData,
    ProjectData,
    counts_toward_concurrency,
)

_EPS = 1e-6  # 부동소수 비교 허용오차


def _ym(mi: int) -> str:
    """월 인덱스 → 'YYYY-MM' 표기."""
    year = (mi - 1) // 12
    return f"{year}-{mi - year * 12:02d}"


def audit_distribution(
    results,
    members: list[MemberData],
    projects: list[ProjectData],
    today: date,
) -> list[str]:
    """최종 배분 결과의 규정 위반 목록을 반환한다 (비어 있으면 전 규칙 통과).

    results 원소는 .project_id/.member_id/.role/.start_date/.end_date/.rate/.cost
    속성만 있으면 된다 (ParticipationResult, DB Participation 모두 호환).
    """
    violations: list[str] = []
    member_map = {m.id: m for m in members}
    proj_map = {p.id: p for p in projects}

    # ── A. 세그먼트 단위 검사 ──
    for r in results:
        m = member_map.get(r.member_id)
        p = proj_map.get(r.project_id)
        if not m or not p:
            violations.append(f"[고아 레코드] 존재하지 않는 {'연구원' if not m else '사업'} 참조: {r.id}")
            continue
        tag = f"[{p.name}] {m.name}"
        s, e = to_month_idx(r.start_date), to_month_idx(r.end_date)

        if s > e:
            violations.append(f"{tag} 기간 역전: {r.start_date} > {r.end_date}")
            continue
        if s < to_month_idx(p.start_date) or e > to_month_idx(p.end_date):
            violations.append(f"{tag} 사업기간({p.start_date}~{p.end_date}) 밖 배정: {r.start_date}~{r.end_date}")
        if m.hire_date and s < to_month_idx(m.hire_date):
            violations.append(f"{tag} 입사({m.hire_date}) 전 배정: {r.start_date}~")
        if m.resign_date and e > to_month_idx(m.resign_date):
            violations.append(f"{tag} 퇴사({m.resign_date}) 후 배정: ~{r.end_date}")
        if r.rate < MIN_PARTICIPATION_RATE - _EPS:
            violations.append(f"{tag} 최소 참여율 미달: {r.rate:.2f}% < {MIN_PARTICIPATION_RATE}%")
        if abs(r.cost % ROUNDING_UNIT) > _EPS:
            violations.append(f"{tag} 인건비가 천원 단위가 아님: {r.cost:,.0f}원")
        mon = e - s + 1
        ceiling = m.salary * mon * r.rate / 100
        if r.cost > ceiling + _EPS:
            violations.append(f"{tag} 초과 계상: {r.cost:,.0f}원 > 급여×개월×참여율 {ceiling:,.0f}원")

    # ── B. 월별 검사 (연구원 × 월) ──
    for m in members:
        rows = [r for r in results if r.member_id == m.id and r.project_id in proj_map]
        month_set = {mi for r in rows for mi in range(to_month_idx(r.start_date), to_month_idx(r.end_date) + 1)}
        nat_cap = min(m.max_rate, settings.nat_rate_cap)
        for mi in sorted(month_set):
            active = [r for r in rows if to_month_idx(r.start_date) <= mi <= to_month_idx(r.end_date)]

            nat_sum = sum(r.rate for r in active if proj_map[r.project_id].funding_source == NAT_FUNDING)
            total_sum = sum(r.rate for r in active)
            if nat_sum > nat_cap + _EPS:
                violations.append(f"{m.name} {_ym(mi)} 정부수탁 참여율 합 {nat_sum:.2f}% > 상한 {nat_cap:.0f}%")
            if total_sum > settings.total_rate_cap + _EPS:
                violations.append(
                    f"{m.name} {_ym(mi)} 전체 참여율 합 {total_sum:.2f}% > 상한 {settings.total_rate_cap:.0f}%"
                )

            # 5공: 카운트 대상(잔여 6개월 미만 제외·단장 예외) 동시 사업 수
            countable = {
                r.project_id
                for r in active
                if counts_toward_concurrency(m.rank, proj_map[r.project_id].end_date, today)
            }
            if len(countable) > m.max_projects:
                violations.append(
                    f"{m.name} {_ym(mi)} 동시 참여 {len(countable)}개 > 상한 {m.max_projects}개 (5공)"
                )

            # 3책: '주관 사업 연구책임자' 역할 동시 수
            chief = {
                r.project_id
                for r in active
                if r.role == "연구책임자"
                and proj_map[r.project_id].org_role == "주관"
                and counts_toward_concurrency(m.rank, proj_map[r.project_id].end_date, today)
            }
            if len(chief) > MAX_CHIEF_PROJECTS:
                violations.append(
                    f"{m.name} {_ym(mi)} 주관 연구책임자 {len(chief)}개 > 상한 {MAX_CHIEF_PROJECTS}개 (3책)"
                )

    # ── C. 예산 검사 ──
    for p in projects:
        p_rows = [r for r in results if r.project_id == p.id and r.member_id in member_map]
        if not p_rows:
            continue
        total_alloc = sum(r.cost for r in p_rows)
        total_budget = sum(float(v or 0) for v in p.year_budgets.values())
        if total_alloc > total_budget + _EPS:
            violations.append(f"[{p.name}] 총 배분액 {total_alloc:,.0f}원 > 총예산 {total_budget:,.0f}원")

        # 연도별: 세그먼트가 연도를 걸치면(병합 결과) 월수 비례로 나눠 귀속시킨다.
        # 원 세그먼트별 내림(천원) 때문에 ±1000원 단위 오차가 가능하므로 행당 ROUNDING_UNIT 허용.
        year_alloc: dict[int, float] = {}
        year_rows: dict[int, int] = {}
        for r in p_rows:
            s, e = to_month_idx(r.start_date), to_month_idx(r.end_date)
            mon = e - s + 1
            for y in range(int(r.start_date[:4]), int(r.end_date[:4]) + 1):
                y_s = max(s, to_month_idx(f"{y}-01-01"))
                y_e = min(e, to_month_idx(f"{y}-12-31"))
                mon_y = y_e - y_s + 1
                if mon_y <= 0:
                    continue
                year_alloc[y] = year_alloc.get(y, 0.0) + r.cost * mon_y / mon
                year_rows[y] = year_rows.get(y, 0) + 1
        for y, alloc in sorted(year_alloc.items()):
            budget_y = float(p.year_budgets.get(str(y), 0) or 0)
            tolerance = ROUNDING_UNIT * (year_rows[y] + 1)
            if alloc > budget_y + tolerance:
                violations.append(f"[{p.name}] {y}년 배분액 {alloc:,.0f}원 > 연도 예산 {budget_y:,.0f}원")

    return violations
