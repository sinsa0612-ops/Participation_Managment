from pydantic import BaseModel


class ParticipationOut(BaseModel):
    id: str
    project_id: str
    member_id: str
    role: str
    start_date: str
    end_date: str
    rate: float
    cost: float
    # 조인/파생 필드 (서비스 레이어에서 채움)
    member_name: str | None = None
    employ_type: str | None = None
    rank: str | None = None
    proj_name: str | None = None
    months: int | None = None
    monthly_cost: float | None = None  # 월별 인건비(천원 내림) — 프론트 재계산 방지용 SSOT 값

    model_config = {"from_attributes": True}


class MemberStatOut(BaseModel):
    member_id: str
    member_name: str
    employ_type: str
    rank: str
    proj_count: int
    max_concurrent: int
    total_rate: float
    total_cost: float
    max_rate: float
    max_projects: int
    status: str  # 정상 | 미배분 | 초과


class BudgetDiagOut(BaseModel):
    project_id: str
    project_name: str
    budget: float
    allocated: float
    remaining: float
    reason: str  # ok | no_budget | saturated | slack
    detail: str
    recruitable: list[str] = []


class DistributeResult(BaseModel):
    participations: list[ParticipationOut]
    warnings: list[str] = []  # 강제 참여시켰으나 예산·상한으로 배정 못한 (사업, 연구원) 경고 (#4)
