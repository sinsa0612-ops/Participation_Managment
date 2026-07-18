from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.ids import new_id
from app.models.member import Member
from app.models.project import (
    Project,
    ProjectBudget,
    ProjectRequirement,
    ProjectConstraint,
    ProjectMemberMonth,
    ProjectExclusion,
)
from app.models.participation import Participation
from app.models.override import ParticipationOverride
from app.schemas.participation import ParticipationOut, MemberStatOut, BudgetDiagOut, DistributeResult
from app.schemas.override import OverrideIn, OverrideOut
from app.services import calc
from app.services.stats import compute_member_stats
from app.services.budget import compute_budget_diagnostics
from app.services.distribute import (
    auto_distribute,
    MemberData,
    ProjectData,
    ParticipationResult,
    _clamp_months,
    _to_month_idx,
)

router = APIRouter(prefix="/participations", tags=["participations"])


def _max_concurrent_rate(parts, member_id: str, exclude_project_id: str, start_date: str, end_date: str) -> float:
    """[start_date, end_date] 구간에서 해당 연구원의 '다른 사업' 월 참여율 합의 최댓값.

    parts 원소는 .member_id/.project_id/.start_date/.end_date/.rate 속성을 가지면 된다
    (Participation, ParticipationResult 모두 호환).
    """
    s, e = _to_month_idx(start_date), _to_month_idx(end_date)
    peak = 0.0
    for mi in range(s, e + 1):
        concurrent = sum(
            x.rate
            for x in parts
            if x.member_id == member_id
            and x.project_id != exclude_project_id
            and _to_month_idx(x.start_date) <= mi <= _to_month_idx(x.end_date)
        )
        peak = max(peak, concurrent)
    return peak


def _apply_overrides(results: list[ParticipationResult], members: list[Member], projects: list[Project], db: Session):
    """수동 조정값(F12)을 배분 결과에 재적용 — 참여율을 덮되, 월 참여율 상한을 넘지 않게 클램프한다.

    같은 연구원의 겹치는 사업에 여러 조정이 걸려도 최종 월 합계가 max_rate를 넘지 않도록,
    사업 종료일 순으로 처리하며 각 조정을 '이미 반영된 다른 결과들' 기준으로 클램프한다.
    """
    overrides = {(o.project_id, o.member_id): o.rate for o in db.query(ParticipationOverride).all()}
    if not overrides:
        return
    member_map = {m.id: m for m in members}
    project_map = {p.id: p for p in projects}

    def order_key(r: ParticipationResult):
        p = project_map.get(r.project_id)
        return (p.end_date if p else "", r.member_id)

    for r in sorted(results, key=order_key):
        rate = overrides.get((r.project_id, r.member_id))
        if rate is None:
            continue
        m = member_map.get(r.member_id)
        p = project_map.get(r.project_id)
        if not m or not p:
            continue
        peak = _max_concurrent_rate(results, r.member_id, r.project_id, r.start_date, r.end_date)
        applied = min(rate, max(0.0, m.max_rate - peak))  # 월 100%(=max_rate) 초과 금지
        mon = _clamp_months(p.start_date, p.end_date, r.start_date, r.end_date)
        r.rate = round(applied, 2)
        r.cost = calc.period_cost(m.salary, r.rate, mon)


def _member_data(m: Member) -> MemberData:
    return MemberData(
        id=m.id,
        name=m.name,
        employ_type=m.employ_type,
        rank=m.rank,
        salary=m.salary,
        max_rate=m.max_rate,
        max_projects=m.max_projects,
        hire_date=m.hire_date,
        resign_date=m.resign_date,
    )


def _project_data(p: Project, db: Session) -> ProjectData:
    budgets = db.query(ProjectBudget).filter(ProjectBudget.project_id == p.id).all()
    reqs = db.query(ProjectRequirement).filter(ProjectRequirement.project_id == p.id).all()
    cons = db.query(ProjectConstraint).filter(ProjectConstraint.project_id == p.id).all()
    month_rows = db.query(ProjectMemberMonth).filter(ProjectMemberMonth.project_id == p.id).all()

    year_budgets: dict[str, float] = {}
    for b in budgets:
        year_budgets[b.year] = year_budgets.get(b.year, 0.0) + b.amount

    chief = next((r.member_id for r in reqs if r.role == "chief"), None)
    staff = [r.member_id for r in reqs if r.role == "staff"]
    constraints = {c.member_id: c.max_rate for c in cons}

    member_months: dict[str, list[str]] = {}
    for row in month_rows:
        member_months.setdefault(row.member_id, []).append(row.year_month)

    excluded = [e.member_id for e in db.query(ProjectExclusion).filter(ProjectExclusion.project_id == p.id).all()]

    return ProjectData(
        id=p.id,
        name=p.name,
        start_date=p.start_date,
        end_date=p.end_date,
        year_budgets=year_budgets,
        required_chief=chief,
        required_staff=staff,
        member_constraints=constraints,
        member_months=member_months,
        sort_order=p.sort_order,
        excluded_members=excluded,
    )


def _enrich(r: ParticipationResult, members: list[Member], projects: list[Project]) -> ParticipationOut:
    m = next((x for x in members if x.id == r.member_id), None)
    p = next((x for x in projects if x.id == r.project_id), None)
    mon = _clamp_months(p.start_date, p.end_date, r.start_date, r.end_date) if p else 0
    return ParticipationOut(
        id=r.id,
        project_id=r.project_id,
        member_id=r.member_id,
        role=r.role,
        start_date=r.start_date,
        end_date=r.end_date,
        rate=r.rate,
        cost=r.cost,
        member_name=m.name if m else None,
        employ_type=m.employ_type if m else None,
        rank=m.rank if m else None,
        proj_name=p.name if p else None,
        months=mon,
        monthly_cost=calc.monthly_cost(m.salary, r.rate) if m else None,
    )


def _forced_warnings(project_data_list, members, results) -> list[str]:
    """강제 참여(member_months)시켰으나 예산·상한으로 끝내 배정 못한 (사업, 연구원) 경고 (#4)."""
    assigned = {(r.project_id, r.member_id) for r in results}
    member_name = {m.id: m.name for m in members}
    warnings: list[str] = []
    for p in project_data_list:
        for mid in p.member_months:
            if mid in p.excluded_members:
                continue
            if (p.id, mid) not in assigned:
                warnings.append(f"[{p.name}] {member_name.get(mid, mid)} 강제 참여 실패 — 예산·참여율 상한 부족")
    return warnings


@router.post("/distribute", response_model=DistributeResult)
def run_distribute(db: Session = Depends(get_db)):
    """자동 배분 실행 — 기존 결과를 삭제하고 재계산한 후 DB에 저장. 강제 참여 실패는 warnings로 안내."""
    members = db.query(Member).all()
    projects = db.query(Project).all()

    member_data_list = [_member_data(m) for m in members]
    project_data_list = [_project_data(p, db) for p in projects]

    results = auto_distribute(project_data_list, member_data_list)
    _apply_overrides(results, members, projects, db)  # 수동 조정값 재적용 (F12)

    db.query(Participation).delete()
    for r in results:
        db.add(
            Participation(
                id=r.id,
                project_id=r.project_id,
                member_id=r.member_id,
                role=r.role,
                start_date=r.start_date,
                end_date=r.end_date,
                rate=r.rate,
                cost=r.cost,
            )
        )
    db.commit()

    return DistributeResult(
        participations=[_enrich(r, members, projects) for r in results],
        warnings=_forced_warnings(project_data_list, members, results),
    )


@router.get("/", response_model=list[ParticipationOut])
def list_participations(db: Session = Depends(get_db)):
    """저장된 배분 결과 조회"""
    rows = db.query(Participation).all()
    members = db.query(Member).all()
    projects = db.query(Project).all()

    out = []
    for row in rows:
        m = next((x for x in members if x.id == row.member_id), None)
        p = next((x for x in projects if x.id == row.project_id), None)
        mon = _clamp_months(p.start_date, p.end_date, row.start_date, row.end_date) if p else 0
        out.append(
            ParticipationOut(
                id=row.id,
                project_id=row.project_id,
                member_id=row.member_id,
                role=row.role,
                start_date=row.start_date,
                end_date=row.end_date,
                rate=row.rate,
                cost=row.cost,
                member_name=m.name if m else None,
                employ_type=m.employ_type if m else None,
                rank=m.rank if m else None,
                proj_name=p.name if p else None,
                months=mon,
                monthly_cost=calc.monthly_cost(m.salary, row.rate) if m else None,
            )
        )
    return out


@router.get("/stats", response_model=list[MemberStatOut])
def member_stats(db: Session = Depends(get_db)):
    """연구원별 참여 현황 통계 — 측정 규칙은 services/stats.py(SSOT)에 위임.

    total_rate=월별 동시 참여율 피크, max_concurrent=카운트 대상(잔여 6개월 미만 제외) 동시참여 피크.
    """
    members = db.query(Member).all()
    rows = db.query(Participation).all()
    projects = db.query(Project).all()

    stats = compute_member_stats(members, rows, projects, settings.base_date)
    return [MemberStatOut(**asdict(s)) for s in stats]


@router.get("/budget-status", response_model=list[BudgetDiagOut])
def budget_status(db: Session = Depends(get_db)):
    """사업별 예산 미소진 '사유' 진단 (F17/Path A) — 알고리즘 무수정, 읽기 전용 설명."""
    members = db.query(Member).all()
    projects = db.query(Project).all()
    rows = db.query(Participation).all()

    member_data_list = [_member_data(m) for m in members]
    project_data_list = [_project_data(p, db) for p in projects]

    diags = compute_budget_diagnostics(project_data_list, member_data_list, rows, settings.base_date)
    return [BudgetDiagOut(**asdict(d)) for d in diags]


# ── 수동 조정(F12) ──
@router.get("/overrides", response_model=list[OverrideOut])
def list_overrides(db: Session = Depends(get_db)):
    """현재 설정된 수동 참여율 조정 목록."""
    return db.query(ParticipationOverride).all()


@router.put("/override", response_model=OverrideOut)
def set_override(body: OverrideIn, db: Session = Depends(get_db)):
    """(사업, 연구원) 조합의 참여율을 수동 지정/갱신. 다음 재배분부터 자동 재적용된다."""
    if not db.get(Project, body.project_id):
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다")
    member = db.get(Member, body.member_id)
    if not member:
        raise HTTPException(status_code=404, detail="연구원을 찾을 수 없습니다")

    # 월 참여율 상한 검증 (F12): 마지막 배분 기준, 같은 기간 다른 사업과 합쳐 상한 초과 금지
    part = (
        db.query(Participation)
        .filter(Participation.project_id == body.project_id, Participation.member_id == body.member_id)
        .first()
    )
    if part:
        others = db.query(Participation).filter(Participation.member_id == body.member_id).all()
        peak = _max_concurrent_rate(others, body.member_id, body.project_id, part.start_date, part.end_date)
        avail = member.max_rate - peak
        if body.rate > avail + 1e-6:
            raise HTTPException(
                status_code=400,
                detail=f"월 참여율 {member.max_rate:.0f}% 초과: 이 기간 여유 {max(0.0, avail):.2f}% (요청 {body.rate:.2f}%)",
            )

    existing = (
        db.query(ParticipationOverride)
        .filter(ParticipationOverride.project_id == body.project_id, ParticipationOverride.member_id == body.member_id)
        .first()
    )
    if existing:
        existing.rate = body.rate
    else:
        existing = ParticipationOverride(
            id=new_id(), project_id=body.project_id, member_id=body.member_id, rate=body.rate
        )
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


@router.delete("/override", status_code=204)
def delete_override(project_id: str, member_id: str, db: Session = Depends(get_db)):
    """수동 조정 해제 — 다음 재배분부터 자동 계산값으로 되돌아간다."""
    db.query(ParticipationOverride).filter(
        ParticipationOverride.project_id == project_id, ParticipationOverride.member_id == member_id
    ).delete()
    db.commit()
