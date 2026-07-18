"""연구원별 참여 현황 통계 계산 (월별 피크 기준, SSOT).

'참여 현황' 화면이 쓰는 측정값을 한 곳에서 계산한다.
- 참여율 합계 = 그 달의 동시 참여율 합의 최댓값(월별 피크). 안 겹치는 달까지 더한 단순합이 아니다.
- 최대 동시참여 = 잔여 6개월 미만 사업을 제외한 '카운트 대상' 동시참여의 월별 피크
  (distribute.is_project_countable 규칙을 그대로 공유한다).

DB 모델과 분리된 순수 함수라 인메모리로 결정적 테스트가 가능하다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.services.calc import to_month_idx
from app.services.distribute import counts_toward_concurrency


@dataclass
class MemberStatData:
    member_id: str
    member_name: str
    employ_type: str
    rank: str
    proj_count: int  # 생애 참여 사업수(중복 제외) — 정보용
    max_concurrent: int  # 카운트 대상 동시참여의 월별 피크 — 상한 판정 기준
    total_rate: float  # 월별 동시 참여율 합의 피크
    total_cost: float
    max_rate: float
    max_projects: int
    status: str  # 정상 | 미배분 | 초과


def compute_member_stats(members, participations, projects, today: date) -> list[MemberStatData]:
    """연구원별 참여 통계 산출.

    members/participations/projects는 속성 접근(.id, .member_id 등)만 요구한다(ORM·테스트 스텁 호환).
    """
    proj_end = {p.id: p.end_date for p in projects}

    out: list[MemberStatData] = []
    for m in members:
        mine = [r for r in participations if r.member_id == m.id]
        proj_count = len({r.project_id for r in mine})

        # 참여가 걸친 모든 월을 순회하며 '그 달' 기준 피크를 구한다.
        months: set[int] = set()
        for r in mine:
            for mi in range(to_month_idx(r.start_date), to_month_idx(r.end_date) + 1):
                months.add(mi)

        peak_rate = 0.0
        peak_concurrent = 0
        for mi in months:
            active = [r for r in mine if to_month_idx(r.start_date) <= mi <= to_month_idx(r.end_date)]
            rate_sum = sum(r.rate for r in active)
            countable = sum(
                1
                for r in active
                if r.project_id in proj_end and counts_toward_concurrency(m.rank, proj_end[r.project_id], today)
            )
            peak_rate = max(peak_rate, rate_sum)
            peak_concurrent = max(peak_concurrent, countable)

        total_cost = sum(r.cost for r in mine)
        over_proj = peak_concurrent > m.max_projects
        over_rate = peak_rate > m.max_rate + 0.01
        if proj_count == 0:
            status = "미배분"
        elif over_proj or over_rate:
            status = "초과"
        else:
            status = "정상"

        out.append(
            MemberStatData(
                member_id=m.id,
                member_name=m.name,
                employ_type=m.employ_type,
                rank=m.rank,
                proj_count=proj_count,
                max_concurrent=peak_concurrent,
                total_rate=peak_rate,
                total_cost=total_cost,
                max_rate=m.max_rate,
                max_projects=m.max_projects,
                status=status,
            )
        )
    return out
