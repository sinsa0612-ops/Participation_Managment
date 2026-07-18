"""
인건비·기간 계산의 단일 진실 공급원(SSOT).

이 프로젝트의 '돈 계산 규칙'은 오직 이 모듈에만 존재한다.
- distribute.py(배분 알고리즘)와 라우터(_enrich 등)가 이 함수들을 공유한다.
- 프론트엔드는 같은 규칙을 다시 구현하지 않고, 백엔드가 내려주는 값(monthly_cost 등)을 소비한다.
  => 규칙이 바뀌면 이 파일 한 곳만 고치면 된다.
"""

from __future__ import annotations

import calendar as _cal
import math
from datetime import date

# 인건비는 천원 단위로 내림(절사)한다.
ROUNDING_UNIT = 1000


def round_down_to_unit(amount: float, unit: int = ROUNDING_UNIT) -> float:
    """amount를 unit 단위로 내림."""
    return math.floor(amount / unit) * unit


def monthly_cost(salary: float, rate: float) -> float:
    """월 인건비 = 내림(월급 × 참여율% , 천원). 한 참여 건의 월별 인건비는 모든 달 동일하다."""
    return float(round_down_to_unit(salary * rate / 100))


def period_cost(salary: float, rate: float, months: int) -> float:
    """기간 인건비 = 내림(월급 × 개월 × 참여율% , 천원)."""
    return float(round_down_to_unit(salary * months * rate / 100))


# ──────────────────────────────────────────
# 날짜/기간 유틸 (월 단위 비교)
# ──────────────────────────────────────────


def to_month_idx(d: str) -> int:
    """YYYY-MM-DD → 연*12+월 인덱스."""
    dt = date.fromisoformat(d)
    return dt.year * 12 + dt.month


def clamp_months(a_start: str, a_end: str, b_start: str, b_end: str) -> int:
    """두 기간이 겹치는 개월 수."""
    s = max(to_month_idx(a_start), to_month_idx(b_start))
    e = min(to_month_idx(a_end), to_month_idx(b_end))
    return max(0, e - s + 1)


def month_idx_to_first_day(mi: int) -> str:
    """월 인덱스 → YYYY-MM-01."""
    year = (mi - 1) // 12
    month = mi - year * 12
    return f"{year}-{month:02d}-01"


def month_idx_to_last_day(mi: int) -> str:
    """월 인덱스 → YYYY-MM-DD(말일)."""
    year = (mi - 1) // 12
    month = mi - year * 12
    last_day = _cal.monthrange(year, month)[1]
    return f"{year}-{month:02d}-{last_day:02d}"
