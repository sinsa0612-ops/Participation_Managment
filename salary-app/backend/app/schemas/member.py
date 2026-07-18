from datetime import date as _date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EmployType = Literal["정규직", "전문직", "위촉직"]
Rank = Literal["단장", "센터장", "팀장", "연구원"]


def _validate_iso_date(v: str | None) -> str | None:
    """빈 값은 None으로, 그 외는 YYYY-MM-DD 형식인지 검증."""
    if v is None or v == "":
        return None
    try:
        _date.fromisoformat(v)
    except ValueError as exc:
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다") from exc
    return v


class MemberBase(BaseModel):
    name: str = Field(min_length=1)
    employ_type: EmployType
    rank: Rank
    salary: float = Field(ge=0)  # 음수 급여 불가
    max_rate: float = Field(default=100.0, ge=0, le=100)  # 0~100%
    max_projects: int = Field(default=5, ge=1)
    hire_date: str | None = None
    resign_date: str | None = None
    birth_date: str | None = None
    researcher_no: str | None = None

    @field_validator("hire_date", "resign_date", "birth_date")
    @classmethod
    def _check_dates(cls, v: str | None) -> str | None:
        return _validate_iso_date(v)


class MemberCreate(MemberBase):
    pass


class MemberUpdate(MemberBase):
    pass


class MemberOut(MemberBase):
    id: str
    max_rate: float  # DB 저장값 그대로 반환 — 입력 제약(le=100)을 응답에 적용하지 않음

    model_config = {"from_attributes": True}
