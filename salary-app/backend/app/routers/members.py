import csv
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.ids import new_id
from app.models.member import Member
from app.models.participation import Participation
from app.models.project import ProjectMemberMonth, ProjectRequirement, ProjectConstraint, ProjectExclusion
from app.schemas.member import MemberCreate, MemberUpdate, MemberOut

router = APIRouter(prefix="/members", tags=["members"])

VALID_EMPLOY = {"정규직", "전문직", "위촉직"}
VALID_RANK = {"단장", "센터장", "팀장", "연구원"}


@router.get("/", response_model=list[MemberOut])
def list_members(db: Session = Depends(get_db)):
    return db.query(Member).all()


@router.post("/", response_model=MemberOut, status_code=201)
def create_member(body: MemberCreate, db: Session = Depends(get_db)):
    member = Member(id=new_id(), **body.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/{member_id}", response_model=MemberOut)
def get_member(member_id: str, db: Session = Depends(get_db)):
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="연구원을 찾을 수 없습니다")
    return member


@router.put("/{member_id}", response_model=MemberOut)
def update_member(member_id: str, body: MemberUpdate, db: Session = Depends(get_db)):
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="연구원을 찾을 수 없습니다")
    for key, val in body.model_dump().items():
        setattr(member, key, val)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: str, db: Session = Depends(get_db)):
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="연구원을 찾을 수 없습니다")
    # 고아 레코드 방지 (F7) — 기존 DB는 FK 미적용이므로 멤버를 참조하는 모든 자식 행을 명시적으로 정리
    db.query(Participation).filter(Participation.member_id == member_id).delete()
    db.query(ProjectRequirement).filter(ProjectRequirement.member_id == member_id).delete()
    db.query(ProjectConstraint).filter(ProjectConstraint.member_id == member_id).delete()
    db.query(ProjectMemberMonth).filter(ProjectMemberMonth.member_id == member_id).delete()
    db.query(ProjectExclusion).filter(ProjectExclusion.member_id == member_id).delete()
    db.delete(member)
    db.commit()


@router.post("/import-csv")
async def import_members_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
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

    for i, row in enumerate(reader, 2):
        name = (row.get("이름") or "").strip()
        if not name:
            continue

        employ_type = (row.get("고용형태") or "정규직").strip()
        rank = (row.get("직급") or "연구원").strip()

        if employ_type not in VALID_EMPLOY:
            errors.append(f"행 {i} ({name}): 고용형태 '{employ_type}' 은 정규직/전문직/위촉직 중 하나여야 합니다")
            continue
        if rank not in VALID_RANK:
            errors.append(f"행 {i} ({name}): 직급 '{rank}' 은 단장/센터장/팀장/연구원 중 하나여야 합니다")
            continue

        try:
            salary = float((row.get("월인건비(원)") or "0").strip().replace(",", "") or "0")
            max_rate = float((row.get("국비참여율상한(%)") or "100").strip().replace(",", "") or "100")
            max_projects = int((row.get("최대참여사업수") or "5").strip() or "5")
        except ValueError as e:
            errors.append(f"행 {i} ({name}): 숫자 변환 오류 — {e}")
            continue

        birth_date = (row.get("생년월일") or "").strip() or None
        researcher_no = (row.get("국가연구자번호") or "").strip() or None
        hire_date = (row.get("입사일") or "").strip() or None
        resign_date = (row.get("퇴사일") or "").strip() or None

        member = Member(
            id=new_id(),
            name=name,
            employ_type=employ_type,
            rank=rank,
            salary=salary,
            max_rate=max_rate,
            max_projects=max_projects,
            birth_date=birth_date,
            researcher_no=researcher_no,
            hire_date=hire_date,
            resign_date=resign_date,
        )
        db.add(member)
        created += 1

    db.commit()
    return {"created": created, "errors": errors}
