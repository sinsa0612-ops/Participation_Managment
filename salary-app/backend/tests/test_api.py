"""
API 해피패스 테스트 — 인메모리 DB 격리, TestClient 사용.
멤버·사업 CRUD, 자동 배분, 통계 엔드포인트의 기본 동작을 고정한다.
"""

from __future__ import annotations


def _make_member(client, name="홍길동", **over):
    body = {
        "name": name,
        "employ_type": "정규직",
        "rank": "연구원",
        "salary": 3000000,
        "max_rate": 100,
        "max_projects": 5,
    }
    body.update(over)
    return client.post("/members/", json=body)


def _make_project(client, name="테스트사업", **over):
    body = {
        "name": name,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
        "year_budgets": {"2025": 60000000},
        "required_members": {"chief": None, "staff": []},
        "member_constraints": {},
    }
    body.update(over)
    return client.post("/projects/", json=body)


def test_member_crud(client):
    res = _make_member(client)
    assert res.status_code == 201
    member = res.json()
    mid = member["id"]
    assert member["name"] == "홍길동"

    assert client.get("/members/").json()[0]["id"] == mid

    upd = client.put(
        f"/members/{mid}",
        json={
            "name": "김철수",
            "employ_type": "전문직",
            "rank": "팀장",
            "salary": 4000000,
            "max_rate": 80,
            "max_projects": 3,
        },
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "김철수"
    assert upd.json()["employ_type"] == "전문직"

    assert client.delete(f"/members/{mid}").status_code == 204
    assert client.get("/members/").json() == []


def test_member_not_found(client):
    assert client.get("/members/nope").status_code == 404


def test_project_crud_with_relations(client):
    chief = _make_member(client, name="책임자").json()
    proj = _make_project(client, required_members={"chief": chief["id"], "staff": []}).json()

    fetched = client.get(f"/projects/{proj['id']}").json()
    assert fetched["year_budgets"]["2025"] == 60000000
    assert fetched["required_members"]["chief"] == chief["id"]

    assert client.delete(f"/projects/{proj['id']}").status_code == 204
    assert client.get("/projects/").json() == []


def test_distribute_and_stats(client):
    chief = _make_member(client, name="책임자", salary=5000000).json()
    _make_project(client, required_members={"chief": chief["id"], "staff": []})

    res = client.post("/participations/distribute")
    assert res.status_code == 200
    body = res.json()
    parts = body["participations"]
    assert body["warnings"] == []
    assert len(parts) >= 1
    assert parts[0]["proj_name"] == "테스트사업"
    assert parts[0]["cost"] % 1000 == 0

    # 저장된 결과 재조회
    assert len(client.get("/participations/").json()) == len(parts)

    stats = client.get("/participations/stats").json()
    assert len(stats) == 1
    assert stats[0]["member_name"] == "책임자"
    assert stats[0]["status"] in {"정상", "초과", "미배분"}
    # 측정 불변식 (Phase 1): 참여율 합계는 월별 피크라 단일 사업이면 상한 이내
    assert stats[0]["total_rate"] <= stats[0]["max_rate"] + 0.01
    assert stats[0]["max_concurrent"] <= stats[0]["max_projects"]


def test_project_reorder(client):
    a = _make_project(client, name="A").json()
    b = _make_project(client, name="B").json()
    c = _make_project(client, name="C").json()
    # 생성 순서 A,B,C → 역순으로 재정렬
    res = client.put("/projects/reorder", json={"order": [c["id"], b["id"], a["id"]]})
    assert res.status_code == 200
    names = [p["name"] for p in client.get("/projects/").json()]
    assert names == ["C", "B", "A"]


def test_exclusions_roundtrip_and_distribute(client):
    chief = _make_member(client, name="갑").json()
    proj = _make_project(client, required_members={"chief": chief["id"], "staff": []}).json()
    r = client.put(f"/projects/{proj['id']}/exclusions", json={"member_ids": [chief["id"]]})
    assert r.status_code == 200
    assert client.get(f"/projects/{proj['id']}").json()["excluded_members"] == [chief["id"]]
    body = client.post("/participations/distribute").json()
    assert all(p["member_id"] != chief["id"] for p in body["participations"])  # 제외 → 미배정


def test_forced_assignment_warning(client):
    m = _make_member(client, name="갑", salary=5000000).json()
    proj = _make_project(client, name="박봉사업", year_budgets={"2025": 100000}).json()  # 예산 과소
    client.put(f"/projects/{proj['id']}/member-months", json={"member_months": {m["id"]: ["2025-01", "2025-12"]}})
    body = client.post("/participations/distribute")
    assert body.status_code == 200
    assert any("갑" in w for w in body.json()["warnings"])  # 강제했으나 예산 부족 → 경고


def test_budget_status_endpoint(client):
    chief = _make_member(client, name="책임자", salary=5000000).json()
    _make_project(client, required_members={"chief": chief["id"], "staff": []})
    client.post("/participations/distribute")

    res = client.get("/participations/budget-status")
    assert res.status_code == 200
    diags = res.json()
    assert len(diags) == 1
    assert diags[0]["reason"] in {"ok", "no_budget", "saturated", "slack"}
    assert "budget" in diags[0] and "remaining" in diags[0]


def test_member_months_update(client):
    member = _make_member(client).json()
    proj = _make_project(client).json()

    res = client.put(
        f"/projects/{proj['id']}/member-months",
        json={"member_months": {member["id"]: ["2025-03", "2025-04"]}},
    )
    assert res.status_code == 200

    fetched = client.get(f"/projects/{proj['id']}").json()
    assert fetched["member_months"][member["id"]] == ["2025-03", "2025-04"]


# ── Phase 1: SSOT monthly_cost 노출 ──
def test_response_includes_monthly_cost(client):
    chief = _make_member(client, name="책임자", salary=5000000).json()
    _make_project(client, required_members={"chief": chief["id"], "staff": []})
    parts = client.post("/participations/distribute").json()["participations"]
    assert "monthly_cost" in parts[0]
    assert parts[0]["monthly_cost"] is not None
    assert parts[0]["monthly_cost"] % 1000 == 0


# ── Phase 2: 입구 검증 (F10) ──
def test_member_validation_rejects_bad_values(client):
    assert _make_member(client, salary=-100).status_code == 422
    assert _make_member(client, max_rate=150).status_code == 422
    assert _make_member(client, max_projects=0).status_code == 422
    assert _make_member(client, name="").status_code == 422
    assert _make_member(client, birth_date="아무거나").status_code == 422


def test_project_validation_rejects_bad_period(client):
    assert _make_project(client, start_date="2025-12-31", end_date="2025-01-01").status_code == 422
    assert _make_project(client, start_date="2025-13-99").status_code == 422


# ── Phase 2: 고아 참여 레코드 정리 (F7) ──
def test_delete_member_removes_participations(client):
    chief = _make_member(client, name="책임자", salary=5000000).json()
    _make_project(client, required_members={"chief": chief["id"], "staff": []})
    client.post("/participations/distribute")
    assert len(client.get("/participations/").json()) >= 1

    client.delete(f"/members/{chief['id']}")
    remaining = [p for p in client.get("/participations/").json() if p["member_id"] == chief["id"]]
    assert remaining == []


def test_delete_member_removes_member_months(client):
    """멤버 삭제 시 강제 참여 월(ProjectMemberMonth) 고아 레코드도 정리된다 (F7)."""
    m = _make_member(client).json()
    proj = _make_project(client).json()
    client.put(f"/projects/{proj['id']}/member-months", json={"member_months": {m["id"]: ["2025-03", "2025-04"]}})
    assert client.get(f"/projects/{proj['id']}").json()["member_months"].get(m["id"]) == ["2025-03", "2025-04"]

    client.delete(f"/members/{m['id']}")
    assert m["id"] not in client.get(f"/projects/{proj['id']}").json()["member_months"]


def test_delete_project_removes_participations(client):
    chief = _make_member(client, name="책임자", salary=5000000).json()
    proj = _make_project(client, required_members={"chief": chief["id"], "staff": []}).json()
    client.post("/participations/distribute")
    assert len(client.get("/participations/").json()) >= 1

    client.delete(f"/projects/{proj['id']}")
    remaining = [p for p in client.get("/participations/").json() if p["project_id"] == proj["id"]]
    assert remaining == []


# ── Phase 5: 수동 조정 + 영속성 (F12) ──
def test_override_persists_through_redistribute(client):
    chief = _make_member(client, name="책임자", salary=5000000).json()
    _make_project(client, required_members={"chief": chief["id"], "staff": []})
    parts = client.post("/participations/distribute").json()["participations"]
    proj_id = parts[0]["project_id"]

    # 참여율을 50%로 수동 조정
    res = client.put("/participations/override", json={"project_id": proj_id, "member_id": chief["id"], "rate": 50})
    assert res.status_code == 200

    # 재배분해도 50% 유지 + 인건비 재계산 (2025-01~12 = 12개월)
    parts2 = client.post("/participations/distribute").json()["participations"]
    row = next(p for p in parts2 if p["member_id"] == chief["id"] and p["project_id"] == proj_id)
    assert row["rate"] == 50
    assert row["cost"] == 30000000  # floor(5,000,000 * 12 * 50% / 1000) * 1000

    assert any(o["rate"] == 50 for o in client.get("/participations/overrides").json())


def test_override_can_be_cleared(client):
    chief = _make_member(client, name="책임자", salary=5000000).json()
    _make_project(client, required_members={"chief": chief["id"], "staff": []})
    parts = client.post("/participations/distribute").json()["participations"]
    proj_id = parts[0]["project_id"]
    auto_rate = parts[0]["rate"]

    client.put("/participations/override", json={"project_id": proj_id, "member_id": chief["id"], "rate": 50})
    assert client.delete(f"/participations/override?project_id={proj_id}&member_id={chief['id']}").status_code == 204

    parts2 = client.post("/participations/distribute").json()["participations"]
    row = next(p for p in parts2 if p["member_id"] == chief["id"] and p["project_id"] == proj_id)
    assert row["rate"] == auto_rate  # 자동 계산값으로 복귀


def test_override_validation_and_404(client):
    chief = _make_member(client, name="책임자").json()
    proj = _make_project(client).json()
    # 범위 위반
    assert (
        client.put(
            "/participations/override", json={"project_id": proj["id"], "member_id": chief["id"], "rate": 150}
        ).status_code
        == 422
    )
    # 존재하지 않는 사업
    assert (
        client.put(
            "/participations/override", json={"project_id": "nope", "member_id": chief["id"], "rate": 50}
        ).status_code
        == 404
    )


def test_override_respects_monthly_cap(client):
    """같은 기간 두 사업에 참여한 연구원의 수동 조정이 월 100%를 넘기지 못한다 (F12)."""
    m = _make_member(client, name="갑", salary=5000000).json()
    p1 = _make_project(
        client, name="P1", year_budgets={"2025": 30000000}, required_members={"chief": m["id"], "staff": []}
    ).json()
    _make_project(client, name="P2", year_budgets={"2025": 30000000}, required_members={"chief": m["id"], "staff": []})
    parts = client.post("/participations/distribute").json()["participations"]
    # 자동 배분: 두 사업 합쳐 월 100% 이하 (각 50%)
    assert all(p["member_id"] == m["id"] for p in parts)
    assert sum(p["rate"] for p in parts) <= 100.01

    # P1을 90%로 올리면 P2(50%)와 합쳐 100% 초과 → 거부
    over = client.put("/participations/override", json={"project_id": p1["id"], "member_id": m["id"], "rate": 90})
    assert over.status_code == 400

    # 여유 범위(50%)는 허용
    ok = client.put("/participations/override", json={"project_id": p1["id"], "member_id": m["id"], "rate": 50})
    assert ok.status_code == 200
