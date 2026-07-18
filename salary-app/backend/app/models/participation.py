from sqlalchemy import Column, String, Float, ForeignKey
from app.database import Base


class Participation(Base):
    __tablename__ = "participations"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(String, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # 연구책임자 | 실무자 | 일반참여자
    start_date = Column(String, nullable=False)  # YYYY-MM-DD
    end_date = Column(String, nullable=False)  # YYYY-MM-DD
    rate = Column(Float, nullable=False)  # 참여율 (%)
    cost = Column(Float, nullable=False)  # 인건비 (원, 천원 단위)
