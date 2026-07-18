"""
배분 알고리즘 특성화 테스트 (characterization test).

목적: 리팩토링 전 현재 동작을 '있는 그대로' 고정한다.
seed 데이터로 auto_distribute를 돌린 결과가 baseline_distribution.json과
정확히 일치해야 한다. Phase 3에서 알고리즘을 분해해도 이 스냅샷이 깨지면 안 된다.
(의도된 동작 변경은 사용자 승인 후 baseline 파일을 갱신한다.)
"""

from __future__ import annotations

import json
import os
from datetime import date

from app.services.distribute import (
    auto_distribute,
    _clamp_months,
    _to_month_idx,
)

BASELINE_PATH = os.path.join(os.path.dirname(__file__), "baseline_distribution.json")

# 스냅샷은 고정된 기준일로 계산되어야 결정적이다. (현실 날짜에 의존하지 않음)
BASE_DATE = date(2026, 5, 18)


def _normalize(results):
    # 한 (사업, 연구원)이 연도·기간별로 여러 세그먼트를 가질 수 있으므로 start_date까지 정렬키에 넣어 결정적으로 만든다.
    return sorted(
        [
            {
                "project_id": r.project_id,
                "member_id": r.member_id,
                "role": r.role,
                "start_date": r.start_date,
                "end_date": r.end_date,
                "rate": r.rate,
                "cost": r.cost,
            }
            for r in results
        ],
        key=lambda x: (x["project_id"], x["member_id"], x["start_date"]),
    )


def test_distribution_matches_baseline(algo_inputs):
    members, projects = algo_inputs
    results = auto_distribute(projects, members, today=BASE_DATE)
    snapshot = _normalize(results)

    with open(BASELINE_PATH, encoding="utf-8") as f:
        baseline = json.load(f)

    assert snapshot == baseline


def test_distribution_invariants(algo_inputs):
    """배분 결과가 지켜야 할 불변식 (값이 바뀌어도 깨지면 안 되는 규칙)."""
    members, projects = algo_inputs
    results = auto_distribute(projects, members, today=BASE_DATE)

    # 모든 참여율은 최소 10% 이상
    assert all(r.rate >= 10 for r in results)
    # 모든 인건비는 천원 단위
    assert all(r.cost % 1000 == 0 for r in results)


def test_no_budget_overflow(algo_inputs):
    """사업별 배정액은 예산을 초과하지 않아야 한다 (F17 — Phase 3에서 해결)."""
    from app.services.distribute import _total_budget

    members, projects = algo_inputs
    results = auto_distribute(projects, members, today=BASE_DATE)

    proj_map = {p.id: p for p in projects}
    by_proj: dict[str, float] = {}
    for r in results:
        by_proj[r.project_id] = by_proj.get(r.project_id, 0.0) + r.cost
    for pid, allocated in by_proj.items():
        assert allocated <= _total_budget(proj_map[pid].year_budgets) + 1e-6


# ── 순수 헬퍼 단위 테스트 ──
def test_to_month_idx():
    assert _to_month_idx("2025-01-15") == 2025 * 12 + 1
    assert _to_month_idx("2026-12-01") == 2026 * 12 + 12


def test_clamp_months_full_overlap():
    assert _clamp_months("2025-01-01", "2025-12-31", "2025-01-01", "2025-12-31") == 12


def test_clamp_months_partial_overlap():
    assert _clamp_months("2025-01-01", "2025-06-30", "2025-04-01", "2025-12-31") == 3


def test_clamp_months_no_overlap():
    assert _clamp_months("2025-01-01", "2025-03-31", "2025-06-01", "2025-12-31") == 0
