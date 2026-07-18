from pydantic import BaseModel, Field


class OverrideIn(BaseModel):
    project_id: str
    member_id: str
    rate: float = Field(ge=0, le=100)  # 수동 참여율 (%)


class OverrideOut(OverrideIn):
    id: str

    model_config = {"from_attributes": True}
