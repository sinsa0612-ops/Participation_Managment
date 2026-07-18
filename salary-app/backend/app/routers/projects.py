import csv
import io
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.ids import new_id
from app.models.participation import Participation
from app.models.project import (
    Project,
    ProjectBudget,
    ProjectRequirement,
    ProjectConstraint,
    ProjectMemberMonth,
    ProjectExclusion,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectOut,
    RequiredMembers,
    MemberConstraint,
    MemberMonthsUpdate,
    ExclusionsUpdate,
    ReorderIn,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _build_out(p: Project, db: Session) -> ProjectOut:
    """DB 행 + 관계 테이블 → ProjectOut"""
    budgets = db.query(ProjectBudget).filter(ProjectBudget.project_id == p.id).all()
    reqs = db.query(ProjectRequirement).filter(ProjectRequirement.project_id == p.id).all()
    cons = db.query(ProjectConstraint).filter(ProjectConstraint.project_id == p.id).all()
    month_rows = db.query(ProjectMemberMonth).filter(ProjectMemberMonth.project_id == p.id).all()

    year_budgets: dict[str, float] = {}
    for b in budgets:
        year_budgets[b.year] = year_budgets.get(b.year, 0.0) + b.amount

    chief = next((r.member_id for r in reqs if r.role == "chief"), None)
    staff = [r.member_id for r in reqs if r.role == "staff"]

    member_constraints = {c.member_id: MemberConstraint(max_rate=c.max_rate) for c in cons}

    member_months: dict[str, list[str]] = {}
    for row in month_rows:
        member_months.setdefault(row.member_id, []).append(row.year_month)
    for v in member_months.values():
        v.sort()

    excluded = [e.member_id for e in db.query(ProjectExclusion).filter(ProjectExclusion.project_id == p.id).all()]

    return ProjectOut(
        id=p.id,
        name=p.name,
        start_date=p.start_date,
        end_date=p.end_date,
        year_budgets=year_budgets,
        required_members=RequiredMembers(chief=chief, staff=staff),
        member_constraints=member_constraints,
        member_months=member_months,
        sort_order=p.sort_order,
        excluded_members=excluded,
    )


def _save_relations(project_id: str, body: ProjectCreate | ProjectUpdate, db: Session):
    """연관 테이블(예산·필수참여자·제한) 전체 교체 — member_months는 별도 엔드포인트로 관리"""
    db.query(ProjectBudget).filter(ProjectBudget.project_id == project_id).delete()
    db.query(ProjectRequirement).filter(ProjectRequirement.project_id == project_id).delete()
    db.query(ProjectConstraint).filter(ProjectConstraint.project_id == project_id).delete()

    for yr, total in body.year_budgets.items():
        if float(total or 0):
            db.add(ProjectBudget(id=new_id(), project_id=project_id, year=yr, amount=float(total)))

    if body.required_members.chief:
        db.add(
            ProjectRequirement(id=new_id(), project_id=project_id, member_id=body.required_members.chief, role="chief")
        )
    for mid in body.required_members.staff:
        db.add(ProjectRequirement(id=new_id(), project_id=project_id, member_id=mid, role="staff"))

    for mid, con in body.member_constraints.items():
        db.add(ProjectConstraint(id=new_id(), project_id=project_id, member_id=mid, max_rate=con.max_rate))


@router.get("/", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.sort_order, Project.end_date).all()
    return [_build_out(p, db) for p in projects]


@router.post("/", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    # 신규 사업은 우선순위 목록 맨 뒤에 추가
    max_order = db.query(func.max(Project.sort_order)).scalar()
    p = Project(
        id=new_id(),
        name=body.name,
        start_date=body.start_date,
        end_date=body.end_date,
        sort_order=(max_order or 0) + 1,
    )
    db.add(p)
    db.flush()
    _save_relations(p.id, body, db)
    db.commit()
    return _build_out(p, db)


@router.put("/reorder")
def reorder_projects(body: ReorderIn, db: Session = Depends(get_db)):
    """사업 예산 소진 우선순위 일괄 갱신 — order 리스트의 인덱스가 sort_order가 된다 (#2)."""
    for idx, pid in enumerate(body.order):
        p = db.get(Project, pid)
        if p:
            p.sort_order = idx
    db.commit()
    return {"ok": True}


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다")
    return _build_out(p, db)


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, body: ProjectUpdate, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다")
    p.name = body.name
    p.start_date = body.start_date
    p.end_date = body.end_date
    _save_relations(project_id, body, db)
    db.commit()
    return _build_out(p, db)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다")
    db.query(ProjectBudget).filter(ProjectBudget.project_id == project_id).delete()
    db.query(ProjectRequirement).filter(ProjectRequirement.project_id == project_id).delete()
    db.query(ProjectConstraint).filter(ProjectConstraint.project_id == project_id).delete()
    db.query(ProjectMemberMonth).filter(ProjectMemberMonth.project_id == project_id).delete()
    db.query(ProjectExclusion).filter(ProjectExclusion.project_id == project_id).delete()
    db.query(Participation).filter(Participation.project_id == project_id).delete()  # 고아 참여 방지 (F7)
    db.delete(p)
    db.commit()


@router.post("/import-csv")
async def import_projects_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp949", errors="replace")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    created = 0
    errors: list[str] = []

    # 컬럼에서 연도 추출: "2024년예산(원)" 또는 "2024년예산" 형태
    year_pattern = re.compile(r"^(\d{4})년")

    for i, row in enumerate(reader, 2):
        name = (row.get("사업명") or "").strip()
        if not name:
            continue

        start_date = (row.get("시작일") or "").strip()
        end_date = (row.get("종료일") or "").strip()

        if not start_date or not end_date:
            errors.append(f"행 {i} ({name}): 시작일과 종료일은 필수입니다")
            continue

        year_budgets: dict[str, float] = {}
        for col, val in row.items():
            m = year_pattern.match(col.strip())
            if m:
                amount_str = (val or "").strip().replace(",", "")
                if amount_str:
                    try:
                        year_budgets[m.group(1)] = float(amount_str)
                    except ValueError:
                        errors.append(f"행 {i} ({name}): '{col}' 값 '{val}' 을 숫자로 변환할 수 없습니다")

        p = Project(id=new_id(), name=name, start_date=start_date, end_date=end_date)
        db.add(p)
        db.flush()

        for yr, amount in year_budgets.items():
            if amount:
                db.add(
                    ProjectBudget(
                        id=new_id(),
                        project_id=p.id,
                        year=yr,
                        amount=amount,
                    )
                )

        created += 1

    db.commit()
    return {"created": created, "errors": errors}


@router.put("/{project_id}/member-months", response_model=dict)
def update_member_months(project_id: str, body: MemberMonthsUpdate, db: Session = Depends(get_db)):
    """연구원별 강제 참여 월 전체 교체"""
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다")
    db.query(ProjectMemberMonth).filter(ProjectMemberMonth.project_id == project_id).delete()
    for member_id, months in body.member_months.items():
        for ym in months:
            db.add(
                ProjectMemberMonth(
                    id=new_id(),
                    project_id=project_id,
                    member_id=member_id,
                    year_month=ym,
                )
            )
    db.commit()
    return {"member_months": body.member_months}


@router.put("/{project_id}/exclusions", response_model=dict)
def update_exclusions(project_id: str, body: ExclusionsUpdate, db: Session = Depends(get_db)):
    """이 사업에서 배제할 연구원 전체 교체 (#3)."""
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="사업을 찾을 수 없습니다")
    db.query(ProjectExclusion).filter(ProjectExclusion.project_id == project_id).delete()
    for member_id in dict.fromkeys(body.member_ids):  # 중복 제거
        db.add(ProjectExclusion(id=new_id(), project_id=project_id, member_id=member_id))
    db.commit()
    return {"member_ids": list(dict.fromkeys(body.member_ids))}
