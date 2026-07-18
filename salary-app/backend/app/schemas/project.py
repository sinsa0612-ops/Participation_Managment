from datetime import date as _date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

EmployType = Literal["정규직", "전문직", "위촉직"]


class RequiredMembers(BaseModel):
    chief: str | None = None
    staff: list[str] = []


class MemberConstraint(BaseModel):
    max_rate: float = Field(ge=0, le=100)


class ProjectBase(BaseModel):
    name: str = Field(min_length=1)
    start_date: str
    end_date: str
    year_budgets: dict[str, float] = {}  # { "2025": 125000000.0, ... }
    required_members: RequiredMembers = RequiredMembers()
    member_constraints: dict[str, MemberConstraint] = {}

    @field_validator("start_date", "end_date")
    @classmethod
    def _check_date_format(cls, v: str) -> str:
        try:
            _date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다") from exc
        return v

    @model_validator(mode="after")
    def _check_period(self):
        if self.end_date < self.start_date:
            raise ValueError("종료일은 시작일보다 빠를 수 없습니다")
        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class MemberMonthsUpdate(BaseModel):
    member_months: dict[str, list[str]] = {}


class ExclusionsUpdate(BaseModel):
    member_ids: list[str] = []  # 이 사업에서 배제할 연구원 id 전체 (교체)


class ReorderIn(BaseModel):
    order: list[str] = []  # 사업 id를 원하는 순서대로 — 인덱스가 sort_order가 된다


class ProjectOut(ProjectBase):
    id: str
    member_months: dict[str, list[str]] = {}
    sort_order: int = 0
    excluded_members: list[str] = []

    model_config = {"from_attributes": True}
