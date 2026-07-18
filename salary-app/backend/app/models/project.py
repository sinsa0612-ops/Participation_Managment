from sqlalchemy import Column, String, Float, Integer, ForeignKey, UniqueConstraint
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_date = Column(String, nullable=False)  # YYYY-MM-DD
    end_date = Column(String, nullable=False)  # YYYY-MM-DD
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")  # 예산 소진 우선순위(#2)


class ProjectBudget(Base):
    """연도별 인건비 예산 (연도별 총액, F4).

    예산은 연도별 총액만 사용한다. employ_type은 고용형태별 예산 차원의 잔재로,
    항상 "total"이며 어떤 로직도 이 값에 의존하지 않는다(default로 자동 채움).
    물리적 컬럼 제거는 향후 Alembic 마이그레이션에서 처리한다.
    """

    __tablename__ = "project_budgets"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    year = Column(String, nullable=False)  # "2025"
    employ_type = Column(String, nullable=False, default="total", server_default="total")  # 잔재 — 항상 "total"
    amount = Column(Float, default=0.0)


class ProjectRequirement(Base):
    """필수 참여자 (연구책임자 / 실무자)"""

    __tablename__ = "project_requirements"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(String, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # chief | staff


class ProjectConstraint(Base):
    """사업 한정 연구원별 참여율 상한"""

    __tablename__ = "project_constraints"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(String, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    max_rate = Column(Float, nullable=False)


class ProjectMemberMonth(Base):
    """연구원별 강제 참여 월 (YYYY-MM)"""

    __tablename__ = "project_member_months"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(String, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    year_month = Column(String, nullable=False)  # "YYYY-MM"


class ProjectExclusion(Base):
    """이 사업에서 배제할 연구원 (#3) — 자동 배분 대상에서 제외. (project_id, member_id)당 하나."""

    __tablename__ = "project_exclusions"
    __table_args__ = (UniqueConstraint("project_id", "member_id", name="uq_exclusion_proj_member"),)

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(String, ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
