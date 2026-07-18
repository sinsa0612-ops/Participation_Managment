import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import type { Member, Project, Participation, MemberStat, CsvImportResult, Override, BudgetStatus } from "./api";
import {
  getMembers, createMember, updateMember, deleteMember,
  getProjects, createProject, updateProject, deleteProject,
  runDistribute, getParticipations, getMemberStats,
  importMembersCSV, importProjectsCSV,
  getOverrides, setOverride, deleteOverride,
  getBudgetStatus,
} from "./api";
import { btn } from "./ui/styles";
import { getYears } from "./lib/format";
import { MemberFormModal } from "./components/MemberFormModal";
import { ProjectFormModal } from "./components/ProjectFormModal";
import { MembersTab } from "./components/MembersTab";
import { ProjectsTab } from "./components/ProjectsTab";
import { SummaryTab } from "./components/SummaryTab";
import { MonthlyTab } from "./components/MonthlyTab";
import { DistributionTab } from "./components/DistributionTab";
import { StatsTab } from "./components/StatsTab";

/* ── 기본 폼 값 ── */
const defaultMemForm = (): Omit<Member, "id"> => ({ name: "", employ_type: "정규직", rank: "연구원", salary: 0, max_rate: 100, max_projects: 5, hire_date: null, resign_date: null, birth_date: null, researcher_no: null });
const defaultProjForm = (): Omit<Project, "id"> => ({
  name: "", start_date: "", end_date: "",
  year_budgets: {}, required_members: { chief: null, staff: [] }, member_constraints: {}, member_months: {},
  org_role: "주관", funding_source: "정부수탁",
});

const TABS = ["👥 연구원", "📁 사업", "📊 총괄표", "📅 월별 참여율", "📋 배분결과", "🔍 참여현황"];

/* ── App: 상태 보유 + 탭/모달 오케스트레이션 (뷰는 components/ 로 분리) ── */
export default function App() {
  const [tab, setTab] = useState(0);
  const [members, setMembers] = useState<Member[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [participations, setParticipations] = useState<Participation[]>([]);
  const [stats, setStats] = useState<MemberStat[]>([]);
  const [budgetStatus, setBudgetStatus] = useState<BudgetStatus[]>([]);
  const [overrides, setOverrides] = useState<Override[]>([]);
  const [distWarnings, setDistWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* 모달 상태 */
  const [showMem, setShowMem] = useState(false);
  const [editMemId, setEditMemId] = useState<string | null>(null);
  const [memF, setMemF] = useState(defaultMemForm());

  const [showProj, setShowProj] = useState(false);
  const [editProjId, setEditProjId] = useState<string | null>(null);
  const [projF, setProjF] = useState<Omit<Project, "id">>(defaultProjForm());
  const [selProj, setSelProj] = useState<string | null>(null);

  /* CSV 임포트 */
  const [csvResult, setCsvResult] = useState<{ result: CsvImportResult; type: "연구원" | "사업" } | null>(null);
  const memCsvRef = useRef<HTMLInputElement>(null);
  const projCsvRef = useRef<HTMLInputElement>(null);

  /* 총괄표 / 월별 뷰 */
  const [distYear, setDistYear] = useState(new Date().getFullYear());
  const [selMember, setSelMember] = useState<string | null>(null);

  /* ── 데이터 로드 ── */
  const loadAll = useCallback(async () => {
    try {
      const [m, p, part, s, ov, bs] = await Promise.all([getMembers(), getProjects(), getParticipations(), getMemberStats(), getOverrides(), getBudgetStatus()]);
      setMembers(m); setProjects(p); setParticipations(part); setStats(s); setOverrides(ov); setBudgetStatus(bs);
    } catch (e: unknown) {
      setError("서버 연결 실패: " + (e instanceof Error ? e.message : String(e)));
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const projYears = getYears(projF.start_date, projF.end_date);

  const allYears = useMemo(() => {
    const s = new Set<number>();
    projects.forEach(p => {
      if (p.start_date) s.add(new Date(p.start_date).getFullYear());
      if (p.end_date) s.add(new Date(p.end_date).getFullYear());
    });
    return Array.from(s).sort();
  }, [projects]);

  /* ── CSV ── */
  const handleMemberCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    try {
      const result = await importMembersCSV(file);
      await loadAll();
      setCsvResult({ result, type: "연구원" });
    } catch (err) {
      setError("CSV 업로드 실패: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  };

  const handleProjectCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    try {
      const result = await importProjectsCSV(file);
      await loadAll();
      setCsvResult({ result, type: "사업" });
    } catch (err) {
      setError("CSV 업로드 실패: " + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
      e.target.value = "";
    }
  };

  const downloadTemplate = (type: "member" | "project") => {
    let csv: string;
    let filename: string;
    if (type === "member") {
      csv = "﻿이름,고용형태,직급,월인건비(원),국비참여율상한(%),최대참여사업수,생년월일,국가연구자번호,입사일,퇴사일\n홍길동,정규직,연구원,3000000,100,5,1985-03-15,12345678,2020-01-01,\n김연구,전문직,팀장,4000000,80,3,1980-07-22,,2019-06-01,";
      filename = "연구원_템플릿.csv";
    } else {
      csv = "﻿사업명,시작일,종료일,2024년예산(원),2025년예산(원),2026년예산(원)\n예시사업A,2024-01-01,2025-12-31,50000000,60000000,\n예시사업B,2025-03-01,2026-02-28,,80000000,";
      filename = "사업_템플릿.csv";
    }
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  };

  /* ── 연구원 CRUD ── */
  const openAddMem = () => { setMemF(defaultMemForm()); setEditMemId(null); setShowMem(true); };
  const openEditMem = (m: Member) => {
    setMemF({ name: m.name, employ_type: m.employ_type, rank: m.rank, salary: m.salary, max_rate: m.max_rate, max_projects: m.max_projects, hire_date: m.hire_date ?? null, resign_date: m.resign_date ?? null, birth_date: m.birth_date ?? null, researcher_no: m.researcher_no ?? null });
    setEditMemId(m.id); setShowMem(true);
  };
  const saveMem = async () => {
    if (!memF.name.trim()) return;
    setLoading(true);
    try {
      if (editMemId) await updateMember(editMemId, memF);
      else await createMember(memF);
      setShowMem(false);
      await loadAll();
    } catch (e) {
      setError("연구원 저장 실패: " + (e instanceof Error ? e.message : String(e)));
    } finally { setLoading(false); }
  };
  const delMem = async (id: string) => {
    if (!confirm("삭제하시겠습니까?")) return;
    try {
      await deleteMember(id);
      await loadAll();
    } catch (e) {
      setError("연구원 삭제 실패: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  /* ── 사업 CRUD ── */
  const openAddProj = () => { setProjF(defaultProjForm()); setEditProjId(null); setShowProj(true); };
  const openEditProj = (p: Project) => {
    setProjF({ name: p.name, start_date: p.start_date, end_date: p.end_date, year_budgets: { ...p.year_budgets }, required_members: { ...p.required_members, staff: [...p.required_members.staff] }, member_constraints: { ...p.member_constraints }, member_months: {} });
    setEditProjId(p.id); setShowProj(true);
  };
  const saveProj = async () => {
    if (!projF.name.trim()) return;
    setLoading(true);
    try {
      if (editProjId) await updateProject(editProjId, projF);
      else await createProject(projF);
      setShowProj(false);
      await loadAll();
    } catch (e) {
      setError("사업 저장 실패: " + (e instanceof Error ? e.message : String(e)));
    } finally { setLoading(false); }
  };
  const delProj = async (id: string) => {
    if (!confirm("삭제하시겠습니까?")) return;
    try {
      await deleteProject(id);
      if (selProj === id) setSelProj(null);
      await loadAll();
    } catch (e) {
      setError("사업 삭제 실패: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  /* ── 자동 배분 / 수동 조정 ── */
  const refreshDistribution = async () => {
    const result = await runDistribute();
    setParticipations(result.participations);
    setDistWarnings(result.warnings);
    const [s, ov, bs] = await Promise.all([getMemberStats(), getOverrides(), getBudgetStatus()]);
    setStats(s); setOverrides(ov); setBudgetStatus(bs);
  };
  const handleRunAuto = async () => {
    setLoading(true);
    try { await refreshDistribution(); setTab(2); } finally { setLoading(false); }
  };
  const handleSetOverride = async (projectId: string, memberId: string, rate: number) => {
    setLoading(true);
    try {
      await setOverride(projectId, memberId, rate);
      await refreshDistribution();
    } catch (e) {
      setError("수동 조정 실패: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };
  const handleClearOverride = async (projectId: string, memberId: string) => {
    setLoading(true);
    try {
      await deleteOverride(projectId, memberId);
      await refreshDistribution();
    } catch (e) {
      setError("수동 조정 해제 실패: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ fontFamily: "'Segoe UI',sans-serif", background: "#f0f2f8", height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden" }}>

      {/* ── 헤더 ── */}
      <div style={{ height: 54, flexShrink: 0, background: "#fff", borderBottom: "1px solid #eef0f6", padding: "0 24px", display: "flex", alignItems: "center", justifyContent: "space-between", zIndex: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 22 }}>🗂</span>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#1a1a2e", lineHeight: 1.2 }}>사업비 인건비 배분 관리</div>
            <div style={{ fontSize: 11, color: "#aaa" }}>기준일 {new Date().toLocaleDateString("ko-KR")} · 국비·시비·민간 재원별 자동 배분</div>
          </div>
        </div>
        {error && (
          <div style={{ background: "#ffebee", color: "#c62828", borderRadius: 8, padding: "6px 14px", fontSize: 12, display: "flex", alignItems: "center", gap: 8 }}>
            ⚠ {error}
            <button onClick={() => setError(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#c62828", fontSize: 14, lineHeight: 1 }}>✕</button>
          </div>
        )}
        <button onClick={handleRunAuto} disabled={loading} style={btn("#4f6ef7", "#fff", { padding: "9px 20px", fontSize: 13, borderRadius: 9, boxShadow: "0 2px 8px #4f6ef740", opacity: loading ? 0.7 : 1 } as React.CSSProperties)}>
          {loading ? "처리중..." : "⚡ 자동 배분 실행"}
        </button>
      </div>

      {/* ── CSV 임포트 결과 배너 ── */}
      {csvResult && (
        <div style={{ flexShrink: 0, background: csvResult.result.errors.length > 0 ? "#fff8e1" : "#e8f5e9", borderBottom: "1px solid #eee", padding: "8px 24px", display: "flex", alignItems: "flex-start", gap: 10 }}>
          <div style={{ flex: 1 }}>
            <span style={{ fontWeight: 700, fontSize: 13, color: csvResult.result.errors.length > 0 ? "#e65100" : "#2e7d32" }}>
              {csvResult.type} CSV 업로드 완료 — {csvResult.result.created}건 추가됨
              {csvResult.result.errors.length > 0 && ` / ${csvResult.result.errors.length}건 오류`}
            </span>
            {csvResult.result.errors.length > 0 && (
              <ul style={{ margin: "4px 0 0", paddingLeft: 18, fontSize: 12, color: "#bf360c" }}>
                {csvResult.result.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            )}
          </div>
          <button onClick={() => setCsvResult(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#888", fontSize: 16, lineHeight: 1, flexShrink: 0 }}>✕</button>
        </div>
      )}

      {/* ── 강제 참여 경고 배너 (#4) ── */}
      {distWarnings.length > 0 && (
        <div style={{ flexShrink: 0, background: "#fff8e1", borderBottom: "1px solid #eee", padding: "8px 24px", display: "flex", alignItems: "flex-start", gap: 10 }}>
          <div style={{ flex: 1 }}>
            <span style={{ fontWeight: 700, fontSize: 13, color: "#e65100" }}>⚠ 강제 참여 경고 — {distWarnings.length}건</span>
            <ul style={{ margin: "4px 0 0", paddingLeft: 18, fontSize: 12, color: "#bf360c" }}>
              {distWarnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
          <button onClick={() => setDistWarnings([])} style={{ background: "none", border: "none", cursor: "pointer", color: "#888", fontSize: 16, lineHeight: 1, flexShrink: 0 }}>✕</button>
        </div>
      )}

      {/* ── 바디 ── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* 사이드바 */}
        <div style={{ width: 168, flexShrink: 0, background: "#fff", borderRight: "1px solid #eef0f6", padding: "14px 8px", display: "flex", flexDirection: "column", gap: 2 }}>
          {TABS.map((t, i) => (
            <button key={i} onClick={() => setTab(i)} style={{
              background: tab === i ? "#f0f3ff" : "transparent",
              color: tab === i ? "#4f6ef7" : "#666",
              border: "none",
              borderLeft: `3px solid ${tab === i ? "#4f6ef7" : "transparent"}`,
              borderRadius: "0 9px 9px 0",
              padding: "10px 14px",
              fontSize: 13,
              fontWeight: tab === i ? 700 : 400,
              cursor: "pointer",
              textAlign: "left" as const,
              width: "100%",
            }}>{t}</button>
          ))}
        </div>

        {/* ── 콘텐츠 영역 ── */}
        <div style={{ flex: 1, overflow: "hidden", padding: 16, display: "flex", flexDirection: "column" }}>
          {tab === 0 && (
            <MembersTab
              members={members}
              loading={loading}
              onAdd={openAddMem}
              onEdit={openEditMem}
              onDelete={delMem}
              onCsvUpload={handleMemberCsv}
              onDownloadTemplate={() => downloadTemplate("member")}
              csvRef={memCsvRef}
            />
          )}
          {tab === 1 && (
            <ProjectsTab
              members={members}
              projects={projects}
              selProj={selProj}
              setSelProj={setSelProj}
              loading={loading}
              onAddProj={openAddProj}
              onEditProj={openEditProj}
              onDeleteProj={delProj}
              onDownloadTemplate={() => downloadTemplate("project")}
              onCsvUpload={handleProjectCsv}
              csvRef={projCsvRef}
              onReload={loadAll}
            />
          )}
          {tab === 2 && (
            <SummaryTab
              members={members}
              projects={projects}
              participations={participations}
              budgetStatus={budgetStatus}
              distYear={distYear}
              setDistYear={setDistYear}
              allYears={allYears}
              loading={loading}
              onRedistribute={handleRunAuto}
              onSelectMember={(id) => { setSelMember(id); setTab(3); }}
            />
          )}
          {tab === 3 && (
            <MonthlyTab
              members={members}
              projects={projects}
              participations={participations}
              distYear={distYear}
              setDistYear={setDistYear}
              selMember={selMember}
              setSelMember={setSelMember}
              allYears={allYears}
            />
          )}
          {tab === 4 && (
            <DistributionTab
              participations={participations}
              overrides={overrides}
              loading={loading}
              onRedistribute={handleRunAuto}
              onSetOverride={handleSetOverride}
              onClearOverride={handleClearOverride}
            />
          )}
          {tab === 5 && <StatsTab stats={stats} />}
        </div>{/* /콘텐츠 영역 */}
      </div>{/* /바디 */}

      {/* ── 모달 ── */}
      {showMem && (
        <MemberFormModal form={memF} setForm={setMemF} editing={!!editMemId} onSave={saveMem} onClose={() => setShowMem(false)} />
      )}
      {showProj && (
        <ProjectFormModal form={projF} setForm={setProjF} editing={!!editProjId} members={members} projYears={projYears} onSave={saveProj} onClose={() => setShowProj(false)} />
      )}
    </div>
  );
}
