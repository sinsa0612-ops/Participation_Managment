from sqlalchemy import Column, String, Integer, Float
from app.database import Base


class Member(Base):
    __tablename__ = "members"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    employ_type = Column(String, nullable=False)  # 정규직 | 전문직 | 위촉직
    rank = Column(String, nullable=False)  # 단장 | 센터장 | 팀장 | 연구원
    salary = Column(Float, nullable=False)  # 월 인건비 (원)
    max_rate = Column(Float, default=100.0)  # 국비 참여율 상한 (%)
    max_projects = Column(Integer, default=5)  # 최대 동시 참여 사업 수
    hire_date = Column(String, nullable=True)  # 입사일 (YYYY-MM-DD)
    resign_date = Column(String, nullable=True)  # 퇴사(예정)일 (YYYY-MM-DD)
    birth_date = Column(String, nullable=True)  # 생년월일 (YYYY-MM-DD)
    researcher_no = Column(String, nullable=True)  # 국가연구자번호
