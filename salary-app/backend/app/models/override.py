from sqlalchemy import Column, Float, ForeignKey, String, UniqueConstraint

from app.database import Base


class ParticipationOverride(Base):
    """배분 결과의 수동 참여율 조정값 (F12). (project_id, member_id)당 하나.

    별도 테이블로 두어 자동 배분 결과(participations)와 분리한다.
    재배분할 때마다 이 값이 자동 재적용되어, 수동 조정이 보존된다.
    """

    __tablename__ = "participation_overrides"
    __table_args__ = (UniqueConstraint("project_id", "member_id", name="uq_override_proj_member"),)

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(String, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    rate = Column(Float, nullable=False)  # 수동 지정 참여율 (%)
