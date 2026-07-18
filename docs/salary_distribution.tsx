import { useState, useMemo } from "react";

const EMPLOYMENT_TYPES = ["정규직", "전문직", "위촉직"];
const RANKS = ["단장", "센터장", "팀장", "연구원"];
const ROLES = ["연구책임자", "실무자", "일반참여자"];
const TODAY = new Date(2026, 4, 18); // 2026-05-18

const uid = () => Math.random().toString(36).slice(2, 9);
const fmt = n => n == null ? "-" : Math.round(n).toLocaleString("ko-KR");
const toM = d => { const dt = new Date(d); return dt.getFullYear() * 12 + dt.getMonth(); };
const monthDiff = (a, b) => toM(b) - toM(a) + 1;
const clampMon = (ps, pe, ms, me) => {
  const s = Math.max(toM(ps), toM(ms)), e = Math.min(toM(pe), toM(me));
  return Math.max(0, e - s + 1);
};
const monthsToEnd = endDate => {
  const e = new Date(endDate);
  return (e.getFullYear() - TODAY.getFullYear()) * 12 + (e.getMonth() - TODAY.getMonth());
};

// 연도 목록 추출
const getYears = (start, end) => {
  if (!start || !end) return [];
  const sy = new Date(start).getFullYear(), ey = new Date(end).getFullYear();
  return Array.from({ length: ey - sy + 1 }, (_, i) => sy + i);
};

const lbl = { display: "block", fontSize: 12, fontWeight: 600, color: "#555", marginBottom: 4 };
const inp = (extra = {}) => ({ width: "100%", boxSizing: "border-box", border: "1px solid #e0e0e0", borderRadius: 7, padding: "7px 10px", fontSize: 13, outline: "none", background: "#fafbfc", ...extra });
const tag = (bg, color) => ({ fontSize: 11, background: bg, color, borderRadius: 4, padding: "2px 7px", fontWeight: 600 });
const btn = (bg, color, extra = {}) => ({ background: bg, color, border: "none", borderRadius: 7, padding: "6px 13px", fontSize: 12, fontWeight: 600, cursor: "pointer", ...extra });
const thS = { padding: "7px 8px", textAlign: "center", color: "#666", fontWeight: 600, borderBottom: "1px solid #eee", borderRight: "1px solid #f0f0f0", whiteSpace: "nowrap", fontSize: 12 };
const tdS = { padding: "7px 8px", borderBottom: "1px solid #f5f5f5", borderRight: "1px solid #f0f0f0", whiteSpace: "nowrap", fontSize: 12 };
const ymToStr = mi => { const y = Math.floor(mi / 12); const m = (mi % 12) + 1; return `${y}.${String(m).padStart(2, "0")}`; };

const ROLE_COLOR = { "연구책임자": "#4f6ef7", "실무자": "#26a69a", "일반참여자": "#90a4ae" };
const EMP_COLOR = { "정규직": "#5c6bc0", "전문직": "#00897b", "위촉직": "#f4511e" };

function Modal({ title, onClose, children }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "#0005", zIndex: 300, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "#fff", borderRadius: 16, padding: 28, width: 520, maxWidth: "95vw", maxHeight: "92vh", overflowY: "auto", boxShadow: "0 8px 40px #0003" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>{title}</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 18, cursor: "pointer", color: "#aaa" }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function SaveCancel({ onSave, onClose }) {
  return (
    <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
      <button onClick={onSave} style={btn("#4f6ef7", "#fff", { flex: 1, padding: "10px" })}>저장</button>
      <button onClick={onClose} style={btn("#f5f5f5", "#555", { flex: 1, padding: "10px" })}>취소</button>
    </div>
  );
}

// ───── 자동 배분 알고리즘 ─────
function autoDistribute(projects, members, existingParts) {
  const parts = [];

  // 사업 정렬: 종료일 빠른 순 → 예산 큰 순
  const sortedProjs = [...projects].sort((a, b) => {
    const ed = new Date(a.endDate) - new Date(b.endDate);
    if (ed !== 0) return ed;
    const ta = Object.values(a.yearBudgets || {}).reduce((s: number, v) => s + (parseFloat(v as string) || 0), 0);
    const tb = Object.values(b.yearBudgets || {}).reduce((s: number, v) => s + (parseFloat(v as string) || 0), 0);
    return tb - ta;
  });

  // 연구원별 현재 배분 상태 추적
  // { memberId: [{ projectId, startDate, endDate, rate }] }
  const memberAllocs = {};
  members.forEach(m => { memberAllocs[m.id] = []; });

  // 월별 동시 참여 수 체크
  const getCountableAt = (memberId, monthIdx, projectId) => {
    return memberAllocs[memberId].filter(a => {
      if (a.projectId === projectId) return false;
      const proj = projects.find(p => p.id === a.projectId);
      if (!proj) return false;
      // 해당 월에 참여 중인지
      const inRange = toM(a.startDate) <= monthIdx && toM(a.endDate) >= monthIdx;
      if (!inRange) return false;
      // 6개월 미만 제외 여부: 현재 기준 not 월별 기준
      return monthsToEnd(proj.endDate) >= 6;
    }).length;
  };

  const getTotalRate = (memberId, monthIdx, projectId) => {
    return memberAllocs[memberId].filter(a => a.projectId !== projectId && toM(a.startDate) <= monthIdx && toM(a.endDate) >= monthIdx)
      .reduce((s, a) => s + a.rate, 0);
  };

  const getProjectCount = (memberId, projectId) => {
    const unique = new Set(memberAllocs[memberId].filter(a => a.projectId !== projectId).map(a => a.projectId));
    return unique.size;
  };

  sortedProjs.forEach(proj => {
    if (!proj.startDate || !proj.endDate) return;
    const projStart = proj.startDate, projEnd = proj.endDate;
    const totalBudget = Object.values(proj.yearBudgets || {}).reduce((s: number, v) => s + (parseFloat(v as string) || 0), 0);

    // 필수 참여자: 책임자, 실무자
    const required = proj.requiredMembers || {};
    const chiefId = required.chief;
    const staffIds = required.staff || [];
    const priorityIds = [...new Set([chiefId, ...staffIds].filter(Boolean))];
    const otherIds = members.map(m => m.id).filter(id => !priorityIds.includes(id));
    const orderedIds = [...priorityIds, ...otherIds];

    let remainBudget = totalBudget;

    orderedIds.forEach(memberId => {
      if (remainBudget <= 0) return;
      const member = members.find(m => m.id === memberId);
      if (!member) return;

      const maxRate = parseFloat(member.maxRate) || 100;
      const maxProjs = parseInt(member.maxProjects) || 5;
      const monthlySalary = parseFloat(member.salary) || 0;
      const projConstraint = (proj.memberConstraints || {})[memberId];
      const memberMaxRate = projConstraint?.maxRate != null ? Math.min(parseFloat(projConstraint.maxRate), maxRate) : maxRate;

      // 재직 기간과 사업 기간의 교집합으로 참여 기간 결정
      const mHire = member.hireDate ? toM(member.hireDate) : toM(projStart);
      const mResign = member.resignDate ? toM(member.resignDate) : toM(projEnd);
      if (mHire > toM(projEnd) || mResign < toM(projStart)) return;
      const partStart = mHire > toM(projStart) ? member.hireDate : projStart;
      const partEnd = mResign < toM(projEnd) ? member.resignDate : projEnd;
      const mon = clampMon(projStart, projEnd, partStart, partEnd);
      if (mon <= 0) return;

      // 월별로 가능한 최대 참여율 계산
      let minAvailRate = memberMaxRate;
      for (let mi = toM(partStart); mi <= toM(partEnd); mi++) {
        const cnt = getCountableAt(memberId, mi, proj.id);
        const usedRate = getTotalRate(memberId, mi, proj.id);
        if (cnt >= maxProjs) { minAvailRate = 0; break; }
        const avail = Math.min(memberMaxRate, maxRate - usedRate);
        minAvailRate = Math.min(minAvailRate, avail);
      }

      // 사업 수 제한 체크
      const projCount = getProjectCount(memberId, proj.id);
      if (projCount >= maxProjs) return;
      if (minAvailRate < 10) return; // 최소 10% 불가

      // 예산 기반 참여율 계산
      const totalSalaryFull = monthlySalary * mon;
      if (totalSalaryFull <= 0) return;
      let rateByBudget = Math.min((remainBudget / totalSalaryFull) * 100, minAvailRate);
      // 천원 단위 맞춤
      const salaryPerPct = monthlySalary * mon / 100;
      rateByBudget = Math.floor(rateByBudget * salaryPerPct / 1000) * 1000 / salaryPerPct;
      rateByBudget = Math.round(rateByBudget * 100) / 100;

      if (rateByBudget < 10) return;

      const role = memberId === chiefId ? "연구책임자" : staffIds.includes(memberId) ? "실무자" : "일반참여자";
      const cost = monthlySalary * mon * (rateByBudget / 100);

      parts.push({ id: uid(), projectId: proj.id, memberId, role, startDate: partStart, endDate: partEnd, rate: rateByBudget });
      memberAllocs[memberId].push({ projectId: proj.id, startDate: partStart, endDate: partEnd, rate: rateByBudget });
      remainBudget -= cost;
    });
  });

  // 2차 배분: 잔액 최소화 — 기존 참여자 참여율 상향
  sortedProjs.forEach(proj => {
    if (!proj.startDate || !proj.endDate) return;
    const totalBudget = Object.values(proj.yearBudgets || {}).reduce((s, v) => s + (parseFloat(v) || 0), 0);
    const projParts = parts.filter(p => p.projectId === proj.id);
    if (projParts.length === 0) return;
    const usedBudget = projParts.reduce((s, p) => {
      const member = members.find(m => m.id === p.memberId);
      const mon = clampMon(proj.startDate, proj.endDate, p.startDate, p.endDate);
      return s + Math.round((parseFloat(member?.salary || "0")) * mon * (p.rate / 100) / 1000) * 1000;
    }, 0);
    let remainBudget = totalBudget - usedBudget;
    if (remainBudget < 1000) return;
    for (const part of projParts) {
      if (remainBudget < 1000) break;
      const member = members.find(m => m.id === part.memberId);
      if (!member) continue;
      const maxRate = parseFloat(member.maxRate) || 100;
      const projConstraint = (proj.memberConstraints || {})[part.memberId];
      const memberMaxRate = projConstraint?.maxRate != null ? Math.min(parseFloat(projConstraint.maxRate), maxRate) : maxRate;
      let minAvailRate = memberMaxRate;
      for (let mi = toM(part.startDate); mi <= toM(part.endDate); mi++) {
        const usedRate = getTotalRate(part.memberId, mi, proj.id);
        minAvailRate = Math.min(minAvailRate, Math.min(memberMaxRate, maxRate - usedRate));
      }
      if (minAvailRate <= part.rate + 0.01) continue;
      const mon = clampMon(proj.startDate, proj.endDate, part.startDate, part.endDate);
      const monthlySalary = parseFloat(member.salary) || 0;
      if (monthlySalary <= 0 || mon <= 0) continue;
      const salaryPerPct = monthlySalary * mon / 100;
      const maxAdditional = minAvailRate - part.rate;
      const rateByBudget = Math.min(maxAdditional, (remainBudget / (monthlySalary * mon)) * 100);
      const additionalRate = Math.floor(rateByBudget * salaryPerPct / 1000) * 1000 / salaryPerPct;
      const additionalRateRounded = Math.round(additionalRate * 100) / 100;
      if (additionalRateRounded < 0.01) continue;
      const newRate = Math.round((part.rate + additionalRateRounded) * 100) / 100;
      const additionalCost = monthlySalary * mon * (additionalRateRounded / 100);
      const allocEntry = memberAllocs[part.memberId].find(a => a.projectId === proj.id);
      if (allocEntry) allocEntry.rate = newRate;
      part.rate = newRate;
      remainBudget -= Math.round(additionalCost / 1000) * 1000;
    }
  });

  return parts;
}

export default function App() {
  const [tab, setTab] = useState(0);
  const [members, setMembers] = useState([
    { id: "m1",  name: "김단장", employType: "정규직", rank: "단장",    salary: "6000000", maxRate: "100", maxProjects: "5", hireDate: "2020-03-01", resignDate: "" },
    { id: "m2",  name: "이센터", employType: "정규직", rank: "센터장", salary: "5000000", maxRate: "100", maxProjects: "5", hireDate: "2019-07-01", resignDate: "" },
    { id: "m3",  name: "박팀장", employType: "정규직", rank: "팀장",   salary: "4500000", maxRate: "80",  maxProjects: "4", hireDate: "2021-01-01", resignDate: "" },
    { id: "m4",  name: "최팀장", employType: "전문직", rank: "팀장",   salary: "4000000", maxRate: "100", maxProjects: "5", hireDate: "2022-04-01", resignDate: "" },
    { id: "m5",  name: "정연구", employType: "정규직", rank: "연구원", salary: "3500000", maxRate: "100", maxProjects: "5", hireDate: "2023-01-01", resignDate: "" },
    { id: "m6",  name: "한연구", employType: "전문직", rank: "연구원", salary: "3200000", maxRate: "60",  maxProjects: "3", hireDate: "2023-06-01", resignDate: "" },
    { id: "m7",  name: "윤연구", employType: "정규직", rank: "연구원", salary: "3000000", maxRate: "100", maxProjects: "5", hireDate: "2024-01-01", resignDate: "" },
    { id: "m8",  name: "장연구", employType: "위촉직", rank: "연구원", salary: "2800000", maxRate: "100", maxProjects: "5", hireDate: "2024-03-01", resignDate: "" },
    { id: "m9",  name: "오연구", employType: "위촉직", rank: "연구원", salary: "2500000", maxRate: "100", maxProjects: "5", hireDate: "2024-06-01", resignDate: "2025-09-30" },
    { id: "m10", name: "임연구", employType: "위촉직", rank: "연구원", salary: "2500000", maxRate: "50",  maxProjects: "2", hireDate: "2025-01-01", resignDate: "" },
  ]);

  const [projects, setProjects] = useState([
    {
      id: "p1", name: "스마트시티 AI 플랫폼 개발", startDate: "2025-01-01", endDate: "2026-06-30",
      yearBudgets: { "2025": "125000000", "2026": "63000000" },
      requiredMembers: { chief: "m1", staff: ["m3"] },
      memberConstraints: { m6: { maxRate: "30" } },
    },
    {
      id: "p2", name: "친환경 에너지 효율화 연구", startDate: "2025-03-01", endDate: "2026-02-28",
      yearBudgets: { "2025": "80000000", "2026": "23000000" },
      requiredMembers: { chief: "m2", staff: ["m4"] },
      memberConstraints: { m10: { maxRate: "20" } },
    },
    {
      id: "p3", name: "디지털 헬스케어 플랫폼", startDate: "2025-04-01", endDate: "2025-12-31",
      yearBudgets: { "2025": "71000000" },
      requiredMembers: { chief: "m2", staff: ["m5"] },
      memberConstraints: {},
    },
    {
      id: "p4", name: "자율주행 안전 시스템 구축", startDate: "2025-06-01", endDate: "2026-12-31",
      yearBudgets: { "2025": "57000000", "2026": "67000000" },
      requiredMembers: { chief: "m1", staff: ["m4", "m5"] },
      memberConstraints: { m8: { maxRate: "40" } },
    },
    {
      id: "p5", name: "바이오 데이터 분석 고도화", startDate: "2025-07-01", endDate: "2026-03-31",
      yearBudgets: { "2025": "46000000", "2026": "19000000" },
      requiredMembers: { chief: "m3", staff: ["m6"] },
      memberConstraints: {},
    },
    {
      id: "p6", name: "스마트 물류 최적화 시스템", startDate: "2025-09-01", endDate: "2026-08-31",
      yearBudgets: { "2025": "34000000", "2026": "40000000" },
      requiredMembers: { chief: "m2", staff: ["m7"] },
      memberConstraints: { m10: { maxRate: "30" } },
    },
    {
      id: "p7", name: "공공 빅데이터 활용 연구", startDate: "2026-01-01", endDate: "2026-12-31",
      yearBudgets: { "2026": "89000000" },
      requiredMembers: { chief: "m1", staff: ["m3", "m4"] },
      memberConstraints: {},
    },
  ]);

  const [participations, setParticipations] = useState([]);
  const [distYear, setDistYear] = useState(TODAY.getFullYear());
  const [selMember, setSelMember] = useState(null);

  // 멤버 폼
  const [showMem, setShowMem] = useState(false);
  const [editMemId, setEditMemId] = useState(null);
  const [memF, setMemF] = useState({ name: "", employType: "정규직", rank: "연구원", salary: "", maxRate: "100", maxProjects: "5", hireDate: "", resignDate: "" });

  // 사업 폼
  const [showProj, setShowProj] = useState(false);
  const [editProjId, setEditProjId] = useState(null);
  const [projF, setProjF] = useState({ name: "", startDate: "", endDate: "", yearBudgets: {}, requiredMembers: { chief: "", staff: [] }, memberConstraints: {} });
  const [selProj, setSelProj] = useState(null);

  const projYears = useMemo(() => getYears(projF.startDate, projF.endDate), [projF.startDate, projF.endDate]);

  // 멤버 저장
  const saveMem = () => {
    if (!memF.name.trim()) return;
    if (editMemId) setMembers(ms => ms.map(m => m.id === editMemId ? { ...m, ...memF } : m));
    else setMembers(ms => [...ms, { id: uid(), ...memF }]);
    setShowMem(false);
  };
  const openAddMem = () => { setMemF({ name: "", employType: "정규직", rank: "연구원", salary: "", maxRate: "100", maxProjects: "5", hireDate: "", resignDate: "" }); setEditMemId(null); setShowMem(true); };
  const openEditMem = m => { setMemF({ name: m.name, employType: m.employType, rank: m.rank, salary: m.salary, maxRate: m.maxRate ?? "100", maxProjects: m.maxProjects ?? "5", hireDate: m.hireDate ?? "", resignDate: m.resignDate ?? "" }); setEditMemId(m.id); setShowMem(true); };
  const delMem = id => { setMembers(ms => ms.filter(m => m.id !== id)); setParticipations(ps => ps.filter(p => p.memberId !== id)); };

  // 사업 저장
  const saveProj = () => {
    if (!projF.name.trim()) return;
    if (editProjId) setProjects(ps => ps.map(p => p.id === editProjId ? { ...p, ...projF } : p));
    else setProjects(ps => [...ps, { id: uid(), ...projF }]);
    setShowProj(false);
  };
  const openAddProj = () => { setProjF({ name: "", startDate: "", endDate: "", yearBudgets: {}, requiredMembers: { chief: "", staff: [] }, memberConstraints: {} }); setEditProjId(null); setShowProj(true); };
  const openEditProj = p => { setProjF({ name: p.name, startDate: p.startDate, endDate: p.endDate, yearBudgets: { ...p.yearBudgets }, requiredMembers: { ...p.requiredMembers, staff: [...(p.requiredMembers?.staff || [])] }, memberConstraints: { ...p.memberConstraints } }); setEditProjId(p.id); setShowProj(true); };
  const delProj = id => { setProjects(ps => ps.filter(p => p.id !== id)); setParticipations(ps => ps.filter(p => p.projectId !== id)); if (selProj === id) setSelProj(null); };

  // 자동 배분
  const runAuto = () => {
    const result = autoDistribute(projects, members, participations);
    setParticipations(result);
    setTab(2);
  };

  // 배분 결과 계산
  const distRows = useMemo(() => {
    return participations.map(p => {
      const m = members.find(m => m.id === p.memberId);
      const pr = projects.find(pj => pj.id === p.projectId);
      if (!m || !pr) return null;
      const mon = clampMon(pr.startDate, pr.endDate, p.startDate, p.endDate);
      const salary = parseFloat(m.salary) || 0;
      const cost = Math.round(salary * mon * (p.rate / 100) / 1000) * 1000;
      return { ...p, memberName: m.name, employType: m.employType, rank: m.rank, projName: pr.name, mon, salary, cost };
    }).filter(Boolean);
  }, [participations, members, projects]);

  // 연구원별 참여 현황
  const memberStats = useMemo(() => {
    return members.map(m => {
      const myParts = distRows.filter(r => r.memberId === m.id);
      const projCount = new Set(myParts.map(r => r.projectId)).size;
      const totalRate = myParts.reduce((s, r) => s + r.rate, 0);
      const totalCost = myParts.reduce((s, r) => s + r.cost, 0);
      // 월별 최대 동시 참여
      let maxConcurrent = 0;
      if (myParts.length > 0) {
        const allMonths = new Set(myParts.flatMap(r => {
          const res = [];
          for (let mi = toM(r.startDate); mi <= toM(r.endDate); mi++) res.push(mi);
          return res;
        }));
        allMonths.forEach(mi => {
          const cnt = myParts.filter(r => toM(r.startDate) <= mi && toM(r.endDate) >= mi).length;
          if (cnt > maxConcurrent) maxConcurrent = cnt;
        });
      }
      return { ...m, projCount, totalRate, totalCost, maxConcurrent };
    });
  }, [members, distRows]);

  // 사용 가능 연도 목록
  const allYears = useMemo(() => {
    const yrs = new Set();
    projects.forEach(p => {
      if (p.startDate) yrs.add(new Date(p.startDate).getFullYear());
      if (p.endDate) yrs.add(new Date(p.endDate).getFullYear());
    });
    return Array.from(yrs).sort();
  }, [projects]);

  // 총괄표 데이터 (연도별 프로젝트 × 연구원 비용)
  const summaryData = useMemo(() => {
    const yrStart = distYear * 12;
    const yrEnd = distYear * 12 + 11;
    const activeProjs = projects.filter(p =>
      p.startDate && p.endDate &&
      toM(p.endDate) >= yrStart && toM(p.startDate) <= yrEnd
    );
    const projBudgets = {};
    activeProjs.forEach(p => { projBudgets[p.id] = parseFloat(p.yearBudgets?.[distYear]) || 0; });
    const memberProjCosts = {};
    distRows.forEach(r => {
      if (!activeProjs.find(p => p.id === r.projectId)) return;
      const s_ = Math.max(toM(r.startDate), yrStart);
      const e_ = Math.min(toM(r.endDate), yrEnd);
      const mon = Math.max(0, e_ - s_ + 1);
      if (mon <= 0) return;
      const cost = Math.round((r.salary || 0) * mon * (r.rate / 100) / 1000) * 1000;
      if (!memberProjCosts[r.memberId]) memberProjCosts[r.memberId] = {};
      memberProjCosts[r.memberId][r.projectId] = (memberProjCosts[r.memberId][r.projectId] || 0) + cost;
    });
    const memberRows = members.map((m, idx) => {
      const projCosts = {};
      activeProjs.forEach(p => { projCosts[p.id] = (memberProjCosts[m.id] || {})[p.id] || 0; });
      const totalCost = Object.values(projCosts).reduce((s, v) => s + v, 0);
      const annualSalary = (parseFloat(m.salary) || 0) * 12;
      const totalRate = annualSalary > 0 ? (totalCost / annualSalary) * 100 : 0;
      return { ...m, idx: idx + 1, projCosts, totalCost, totalRate, annualSalary };
    }).filter(m => m.totalCost > 0);
    const projAllocated = {};
    const projRemaining = {};
    activeProjs.forEach(p => {
      projAllocated[p.id] = memberRows.reduce((s, m) => s + (m.projCosts[p.id] || 0), 0);
      projRemaining[p.id] = projBudgets[p.id] - projAllocated[p.id];
    });
    return { activeProjs, projBudgets, memberRows, projAllocated, projRemaining };
  }, [distRows, projects, members, distYear]);

  // 월별 참여율 데이터
  const monthlyData = useMemo(() => {
    if (!selMember) return null;
    const member = members.find(m => m.id === selMember);
    if (!member) return null;
    const yrStart = distYear * 12;
    const yrEnd = distYear * 12 + 11;
    const myParts = distRows.filter(r =>
      r.memberId === selMember &&
      toM(r.endDate) >= yrStart && toM(r.startDate) <= yrEnd
    );
    const projIds = [...new Set(myParts.map(r => r.projectId))];
    const activeProjs = projIds.map(id => projects.find(p => p.id === id)).filter(Boolean);
    const monthlySalary = parseFloat(member.salary) || 0;
    const monthData = Array.from({ length: 12 }, (_, i) => {
      const mo = i + 1;
      const idx = yrStart + i;
      const projRates = {};
      const projCosts = {};
      activeProjs.forEach(p => {
        const part = myParts.find(r => r.projectId === p.id);
        if (part && toM(part.startDate) <= idx && toM(part.endDate) >= idx) {
          projRates[p.id] = part.rate;
          projCosts[p.id] = Math.round(monthlySalary * (part.rate / 100) / 1000) * 1000;
        } else {
          projRates[p.id] = 0;
          projCosts[p.id] = 0;
        }
      });
      const totalRate = Object.values(projRates).reduce((s, v) => s + v, 0);
      const projCount = Object.values(projRates).filter(v => v > 0).length;
      return { mo, projRates, projCosts, totalRate, projCount };
    });
    return { member, activeProjs, monthData, monthlySalary };
  }, [distRows, members, projects, selMember, distYear]);

  const TABS = ["👥 연구원", "📁 사업", "📊 총괄표", "📅 월별 참여율", "🔍 참여현황"];

  return (
    <div style={{ fontFamily: "'Segoe UI',sans-serif", background: "#f4f6fb", minHeight: "100vh", padding: 16 }}>
      <div style={{ maxWidth: 1400, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ background: "#fff", borderRadius: 14, padding: "16px 22px", marginBottom: 12, boxShadow: "0 1px 4px #0001", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#1a1a2e" }}>🗂 사업비 인건비 배분 관리</h1>
            <p style={{ margin: "2px 0 0", color: "#aaa", fontSize: 12 }}>기준일 2026.05.18 | 국비·시비·민간 재원별 자동 배분</p>
          </div>
          <button onClick={runAuto} style={btn("#4f6ef7", "#fff", { padding: "9px 18px", fontSize: 13, borderRadius: 9, boxShadow: "0 2px 8px #4f6ef740" })}>
            ⚡ 자동 배분 실행
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          {TABS.map((t, i) => (
            <button key={i} onClick={() => setTab(i)} style={btn(tab === i ? "#4f6ef7" : "#fff", tab === i ? "#fff" : "#666", { boxShadow: tab === i ? "0 2px 8px #4f6ef740" : "0 1px 3px #0001", padding: "7px 15px" })}>{t}</button>
          ))}
        </div>

        {/* ── TAB 0: 연구원 ── */}
        {tab === 0 && (
          <div style={{ background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <span style={{ fontWeight: 700, fontSize: 15 }}>전체 연구원 ({members.length}명)</span>
              <button onClick={openAddMem} style={btn("#4f6ef7", "#fff")}>+ 연구원 추가</button>
            </div>
            {members.length === 0 && <div style={{ textAlign: "center", color: "#ccc", padding: "40px 0" }}>연구원을 추가하세요</div>}
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              {members.length > 0 && <thead><tr style={{ background: "#f7f8fa" }}>
                {["이름", "고용형태", "직급", "재직기간", "월 인건비", "국비 참여율 상한", "최대 참여 사업수", ""].map(h => (
                  <th key={h} style={{ padding: "8px 10px", textAlign: "left", color: "#666", fontWeight: 600, borderBottom: "1px solid #eee", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr></thead>}
              <tbody>
                {members.map(m => {
                  const hasResign = !!m.resignDate;
                  const resigned = hasResign && toM(m.resignDate) < TODAY.getFullYear() * 12 + TODAY.getMonth();
                  return (
                  <tr key={m.id} style={{ borderBottom: "1px solid #f5f5f5", opacity: resigned ? 0.55 : 1 }}>
                    <td style={{ padding: "9px 10px", fontWeight: 600 }}>{m.name}{resigned && <span style={{ ...tag("#ffebee", "#c62828"), marginLeft: 5 }}>퇴사</span>}</td>
                    <td style={{ padding: "9px 10px" }}><span style={tag(EMP_COLOR[m.employType] + "22", EMP_COLOR[m.employType])}>{m.employType}</span></td>
                    <td style={{ padding: "9px 10px", color: "#555" }}>{m.rank}</td>
                    <td style={{ padding: "9px 10px", fontSize: 11, color: "#777", whiteSpace: "nowrap" }}>
                      {!m.hireDate && !m.resignDate ? <span style={{ color: "#ccc" }}>미설정</span> : (
                        <span>
                          {m.hireDate || "-"}
                          {" ~ "}
                          {m.resignDate
                            ? <span style={{ color: "#e53935", fontWeight: 600 }}>{m.resignDate}</span>
                            : <span style={{ color: "#aaa" }}>재직중</span>}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "9px 10px", color: "#333" }}>₩{fmt(parseFloat(m.salary))}</td>
                    <td style={{ padding: "9px 10px", color: (parseFloat(m.maxRate) || 100) < 100 ? "#e53935" : "#333", fontWeight: (parseFloat(m.maxRate) || 100) < 100 ? 700 : 400 }}>{m.maxRate ?? 100}%</td>
                    <td style={{ padding: "9px 10px", color: (parseInt(m.maxProjects) || 5) < 5 ? "#e53935" : "#333", fontWeight: (parseInt(m.maxProjects) || 5) < 5 ? 700 : 400 }}>{m.maxProjects ?? 5}개</td>
                    <td style={{ padding: "9px 10px" }}>
                      <div style={{ display: "flex", gap: 5 }}>
                        <button onClick={() => openEditMem(m)} style={btn("#f0f3ff", "#4f6ef7")}>수정</button>
                        <button onClick={() => delMem(m.id)} style={btn("#fff0f0", "#e53935")}>삭제</button>
                      </div>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* ── TAB 1: 사업 ── */}
        {tab === 1 && (
          <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 12 }}>
            {/* 사업 목록 */}
            <div style={{ background: "#fff", borderRadius: 14, padding: 18, boxShadow: "0 1px 4px #0001" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <span style={{ fontWeight: 700, fontSize: 14 }}>사업 목록</span>
                <button onClick={openAddProj} style={btn("#4f6ef7", "#fff", { fontSize: 11, padding: "4px 10px" })}>+ 추가</button>
              </div>
              {projects.length === 0 && <div style={{ color: "#ccc", fontSize: 13, textAlign: "center", padding: 20 }}>사업을 추가하세요</div>}
              {projects.map(p => {
                const totalBudget = Object.values(p.yearBudgets || {}).reduce((s: number, v) => s + (parseFloat(v as string) || 0), 0);
                return (
                  <div key={p.id} onClick={() => setSelProj(p.id)} style={{ borderRadius: 9, padding: "10px 12px", marginBottom: 7, cursor: "pointer", border: "1.5px solid", borderColor: selProj === p.id ? "#4f6ef7" : "#eee", background: selProj === p.id ? "#f0f3ff" : "#fafafa" }}>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{p.name}</div>
                    <div style={{ fontSize: 11, color: "#aaa" }}>{p.startDate} ~ {p.endDate}</div>
                    <div style={{ fontSize: 11, color: "#4f6ef7", fontWeight: 600, marginTop: 2 }}>총 ₩{fmt(totalBudget)}</div>
                  </div>
                );
              })}
            </div>

            {/* 사업 상세 */}
            <div style={{ background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001" }}>
              {!selProj ? <div style={{ textAlign: "center", color: "#ccc", padding: "60px 0" }}>사업을 선택하세요</div> : (() => {
                const p = projects.find(pj => pj.id === selProj);
                if (!p) return null;
                const chief = members.find(m => m.id === p.requiredMembers?.chief);
                const staffList = (p.requiredMembers?.staff || []).map(id => members.find(m => m.id === id)).filter(Boolean);
                return (
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                      <div>
                        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{p.name}</h2>
                        <div style={{ fontSize: 12, color: "#aaa", marginTop: 3 }}>{p.startDate} ~ {p.endDate}</div>
                      </div>
                      <div style={{ display: "flex", gap: 6 }}>
                        <button onClick={() => openEditProj(p)} style={btn("#f0f3ff", "#4f6ef7")}>수정</button>
                        <button onClick={() => delProj(p.id)} style={btn("#fff0f0", "#e53935")}>삭제</button>
                      </div>
                    </div>
                    {/* 연도별 예산 + 배분 결과 */}
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: "#333" }}>연도별 인건비 예산</div>
                      {Object.entries(p.yearBudgets || {}).map(([yr, budget]) => {
                        const yrDist = distRows.filter(r => r.projectId === p.id && toM(r.startDate) <= toM(`${yr}-12-31`) && toM(r.endDate) >= toM(`${yr}-01-01`));
                        const empCosts = EMPLOYMENT_TYPES.reduce((acc, et) => {
                          acc[et] = yrDist.filter(r => r.employType === et).reduce((s, r) => {
                            const s_ = Math.max(toM(r.startDate), toM(`${yr}-01-01`));
                            const e_ = Math.min(toM(r.endDate), toM(`${yr}-12-31`));
                            const mon = Math.max(0, e_ - s_ + 1);
                            return s + Math.round((parseFloat(r.salary) || 0) * mon * (r.rate / 100) / 1000) * 1000;
                          }, 0);
                          return acc;
                        }, {} as Record<string, number>);
                        const totalDistributed = Object.values(empCosts).reduce((s, v) => s + v, 0);
                        return (
                          <div key={yr} style={{ background: "#f7f8fa", borderRadius: 8, padding: "10px 12px", marginBottom: 6, fontSize: 13 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span style={{ fontWeight: 600 }}>{yr}년</span>
                              <span style={{ color: "#4f6ef7", fontWeight: 600 }}>예산 ₩{fmt(parseFloat(budget as string) || 0)}</span>
                            </div>
                            {totalDistributed > 0 && (
                              <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px dashed #e0e0e0" }}>
                                <div style={{ fontSize: 11, color: "#999", marginBottom: 4 }}>배분 결과</div>
                                <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                                  {EMPLOYMENT_TYPES.map(et => (
                                    <span key={et} style={{ fontSize: 12, color: EMP_COLOR[et], fontWeight: 600 }}>
                                      {et} ₩{fmt(empCosts[et])}
                                    </span>
                                  ))}
                                  <span style={{ fontSize: 12, color: "#555", marginLeft: "auto" }}>합계 ₩{fmt(totalDistributed)}</span>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    {/* 필수 참여자 */}
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: "#333" }}>필수 참여자</div>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {chief && <span style={tag("#4f6ef722", "#4f6ef7")}>연구책임자: {chief.name}</span>}
                        {staffList.map(m => <span key={m.id} style={tag("#26a69a22", "#26a69a")}>실무자: {m.name}</span>)}
                        {!chief && staffList.length === 0 && <span style={{ color: "#ccc", fontSize: 13 }}>미지정</span>}
                      </div>
                    </div>
                    {/* 참여율 제한 */}
                    {Object.keys(p.memberConstraints || {}).length > 0 && (
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: "#333" }}>연구원별 참여율 상한</div>
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          {Object.entries(p.memberConstraints).map(([mid, c]) => {
                            const m = members.find(m => m.id === mid);
                            return m ? <span key={mid} style={tag("#ff980022", "#e65100")}>{m.name}: 최대 {c.maxRate}%</span> : null;
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        )}

        {/* ── TAB 2: 총괄표 ── */}
        {tab === 2 && (
          <div style={{ background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <span style={{ fontWeight: 700, fontSize: 15 }}>인건비 배분 총괄표</span>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <select style={inp({ width: "auto", padding: "5px 10px" })} value={distYear} onChange={e => setDistYear(Number(e.target.value))}>
                  {allYears.map(y => <option key={y} value={y}>{y}년</option>)}
                </select>
                <button onClick={runAuto} style={btn("#4f6ef7", "#fff")}>⚡ 재배분</button>
              </div>
            </div>
            {distRows.length === 0 ? (
              <div style={{ textAlign: "center", color: "#ccc", padding: "40px 0" }}>자동 배분을 먼저 실행하세요</div>
            ) : summaryData.activeProjs.length === 0 ? (
              <div style={{ textAlign: "center", color: "#ccc", padding: "40px 0" }}>{distYear}년에 진행 중인 사업이 없습니다</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: "100%" }}>
                  <thead>
                    <tr style={{ background: "#f0f3ff" }}>
                      <th rowSpan={4} style={{ ...thS, minWidth: 36, background: "#e8eaf6" }}>연번</th>
                      <th rowSpan={4} style={{ ...thS, minWidth: 72, textAlign: "left", background: "#e8eaf6" }}>이름</th>
                      <th rowSpan={4} style={{ ...thS, minWidth: 90, background: "#e8eaf6" }}>연봉</th>
                      {summaryData.activeProjs.map(p => (
                        <th key={p.id} style={{ ...thS, minWidth: 95, color: "#1a237e", background: "#e8eaf6" }}>{p.name}</th>
                      ))}
                      <th rowSpan={4} style={{ ...thS, minWidth: 95, background: "#e8f5e9", color: "#1b5e20" }}>인건비 합계</th>
                      <th rowSpan={4} style={{ ...thS, minWidth: 72, background: "#e8f5e9", color: "#1b5e20" }}>종참여율</th>
                    </tr>
                    <tr style={{ background: "#f7f8fa" }}>
                      {summaryData.activeProjs.map(p => (
                        <td key={p.id} style={{ ...tdS, textAlign: "center", color: "#888", fontSize: 11 }}>국비</td>
                      ))}
                    </tr>
                    <tr style={{ background: "#f7f8fa" }}>
                      {summaryData.activeProjs.map(p => {
                        const ps = Math.max(toM(p.startDate), distYear * 12);
                        const pe = Math.min(toM(p.endDate), distYear * 12 + 11);
                        return <td key={p.id} style={{ ...tdS, textAlign: "center", color: "#888", fontSize: 11 }}>{ymToStr(ps)}~{ymToStr(pe)}</td>;
                      })}
                    </tr>
                    <tr style={{ background: "#f0f3ff" }}>
                      {summaryData.activeProjs.map(p => (
                        <td key={p.id} style={{ ...tdS, textAlign: "right", fontWeight: 700, color: "#3949ab" }}>
                          ₩{fmt(summaryData.projBudgets[p.id])}
                        </td>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {summaryData.memberRows.map(m => (
                      <tr key={m.id} style={{ borderBottom: "1px solid #f5f5f5" }}
                        onClick={() => { setSelMember(m.id); setTab(3); }}
                        onMouseEnter={e => (e.currentTarget.style.background = "#f8f9ff")}
                        onMouseLeave={e => (e.currentTarget.style.background = "")}>
                        <td style={{ ...tdS, textAlign: "center", color: "#999" }}>{m.idx}</td>
                        <td style={{ ...tdS, fontWeight: 600, cursor: "pointer", color: "#3949ab" }}>{m.name}</td>
                        <td style={{ ...tdS, textAlign: "right", color: "#555" }}>₩{fmt(m.annualSalary)}</td>
                        {summaryData.activeProjs.map(p => (
                          <td key={p.id} style={{ ...tdS, textAlign: "right", color: (m.projCosts[p.id] || 0) > 0 ? "#222" : "#ddd" }}>
                            {(m.projCosts[p.id] || 0) > 0 ? `₩${fmt(m.projCosts[p.id])}` : "-"}
                          </td>
                        ))}
                        <td style={{ ...tdS, textAlign: "right", fontWeight: 700, background: "#f1f8e9", color: "#2e7d32" }}>₩{fmt(m.totalCost)}</td>
                        <td style={{ ...tdS, textAlign: "right", fontWeight: 700, background: "#f1f8e9", color: m.totalRate > 100 ? "#c62828" : "#2e7d32" }}>
                          {m.totalRate.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr style={{ background: "#e8f5e9" }}>
                      <td colSpan={3} style={{ ...tdS, fontWeight: 700, color: "#2e7d32" }}>배정된 금액</td>
                      {summaryData.activeProjs.map(p => (
                        <td key={p.id} style={{ ...tdS, textAlign: "right", fontWeight: 700, color: "#2e7d32" }}>₩{fmt(summaryData.projAllocated[p.id])}</td>
                      ))}
                      <td style={{ ...tdS, textAlign: "right", fontWeight: 700, color: "#2e7d32" }}>
                        ₩{fmt(summaryData.activeProjs.reduce((s, p) => s + summaryData.projAllocated[p.id], 0))}
                      </td>
                      <td style={tdS} />
                    </tr>
                    <tr style={{ background: "#fff3e0" }}>
                      <td colSpan={3} style={{ ...tdS, fontWeight: 700, color: "#e65100" }}>잔액</td>
                      {summaryData.activeProjs.map(p => {
                        const rem = summaryData.projRemaining[p.id];
                        return (
                          <td key={p.id} style={{ ...tdS, textAlign: "right", fontWeight: 700, color: rem < 0 ? "#c62828" : rem === 0 ? "#2e7d32" : "#e65100" }}>
                            ₩{fmt(rem)}
                          </td>
                        );
                      })}
                      <td style={{ ...tdS, textAlign: "right", fontWeight: 700, color: "#e65100" }}>
                        ₩{fmt(summaryData.activeProjs.reduce((s, p) => s + summaryData.projRemaining[p.id], 0))}
                      </td>
                      <td style={tdS} />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 3: 월별 참여율 ── */}
        {tab === 3 && (
          <div style={{ background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001" }}>
            <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
              <span style={{ fontWeight: 700, fontSize: 15 }}>월별 참여율</span>
              <select style={inp({ width: "auto", padding: "5px 10px" })} value={distYear} onChange={e => setDistYear(Number(e.target.value))}>
                {allYears.map(y => <option key={y} value={y}>{y}년</option>)}
              </select>
              <select style={inp({ width: "auto", padding: "5px 10px" })} value={selMember || ""} onChange={e => setSelMember(e.target.value || null)}>
                <option value="">-- 연구원 선택 --</option>
                {members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.employType})</option>)}
              </select>
            </div>
            {!selMember ? (
              <div style={{ textAlign: "center", color: "#ccc", padding: "40px 0" }}>연구원을 선택하세요</div>
            ) : !monthlyData || monthlyData.activeProjs.length === 0 ? (
              <div style={{ textAlign: "center", color: "#ccc", padding: "40px 0" }}>
                {distYear}년 배분 결과가 없습니다. 자동 배분을 실행하세요.
              </div>
            ) : (
              <div>
                <div style={{ display: "flex", gap: 20, marginBottom: 16, padding: "10px 14px", background: "#f7f8fa", borderRadius: 9, flexWrap: "wrap" }}>
                  <span style={{ fontWeight: 700 }}>이름: {monthlyData.member.name}</span>
                  <span style={{ color: "#555" }}>연봉: ₩{fmt((parseFloat(monthlyData.member.salary) || 0) * 12)}</span>
                  <span style={{ color: "#555" }}>월급: ₩{fmt(parseFloat(monthlyData.member.salary) || 0)}</span>
                  <span style={tag(EMP_COLOR[monthlyData.member.employType] + "22", EMP_COLOR[monthlyData.member.employType])}>{monthlyData.member.employType}</span>
                </div>
                <div style={{ overflowX: "auto" }}>
                  {/* 참여율 테이블 */}
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6, color: "#333" }}>월별 참여율 (%)</div>
                  <table style={{ borderCollapse: "collapse", fontSize: 12, marginBottom: 20, minWidth: "100%" }}>
                    <thead>
                      <tr>
                        <th style={{ ...thS, minWidth: 110, textAlign: "left", background: "#e8eaf6" }}>사업명</th>
                        {monthlyData.monthData.map(({ mo, totalRate }) => (
                          <th key={mo} style={{ ...thS, minWidth: 52, background: totalRate > 100 ? "#fff3e0" : "#f0f3ff" }}>{mo}월</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {monthlyData.activeProjs.map((p, pi) => (
                        <tr key={p.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                          <td style={{ ...tdS, fontSize: 11 }}>
                            <span style={{ color: "#aaa", marginRight: 4 }}>{pi + 1}</span>
                            <span style={{ fontWeight: 600 }}>{p.name}</span>
                          </td>
                          {monthlyData.monthData.map(({ mo, projRates }) => {
                            const rate = projRates[p.id];
                            return (
                              <td key={mo} style={{ ...tdS, textAlign: "center", background: rate > 0 ? "#e8f5e9" : "transparent", color: rate > 0 ? "#1b5e20" : "#ddd", fontWeight: rate > 0 ? 600 : 400 }}>
                                {rate > 0 ? `${rate % 1 === 0 ? rate : rate.toFixed(2)}%` : "-"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr style={{ background: "#f0f3ff" }}>
                        <td style={{ ...tdS, fontWeight: 700 }}>합계</td>
                        {monthlyData.monthData.map(({ mo, totalRate }) => (
                          <td key={mo} style={{ ...tdS, textAlign: "center", fontWeight: 700, color: totalRate > 100 ? "#c62828" : totalRate > 0 ? "#3949ab" : "#ddd" }}>
                            {totalRate > 0 ? `${totalRate % 1 === 0 ? totalRate : totalRate.toFixed(2)}%` : "-"}
                          </td>
                        ))}
                      </tr>
                    </tfoot>
                  </table>
                  {/* 인건비 테이블 */}
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6, color: "#333" }}>월별 인건비 (원)</div>
                  <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: "100%" }}>
                    <thead>
                      <tr>
                        <th style={{ ...thS, minWidth: 110, textAlign: "left", background: "#e8eaf6" }}>사업명</th>
                        {monthlyData.monthData.map(({ mo }) => (
                          <th key={mo} style={{ ...thS, minWidth: 72, background: "#f7f8fa" }}>{mo}월</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {monthlyData.activeProjs.map((p, pi) => (
                        <tr key={p.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                          <td style={{ ...tdS, fontSize: 11 }}>
                            <span style={{ color: "#aaa", marginRight: 4 }}>{pi + 1}</span>
                            <span style={{ fontWeight: 600 }}>{p.name}</span>
                          </td>
                          {monthlyData.monthData.map(({ mo, projCosts }) => {
                            const cost = projCosts[p.id];
                            return (
                              <td key={mo} style={{ ...tdS, textAlign: "right", color: cost > 0 ? "#333" : "#ddd", fontSize: 11 }}>
                                {cost > 0 ? fmt(cost) : "-"}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr style={{ background: "#f7f8fa" }}>
                        <td style={{ ...tdS, fontWeight: 700 }}>참여사업개수</td>
                        {monthlyData.monthData.map(({ mo, projCount }) => (
                          <td key={mo} style={{ ...tdS, textAlign: "center", fontWeight: 600, color: projCount > 0 ? "#3949ab" : "#ddd" }}>
                            {projCount > 0 ? `${projCount}개` : "-"}
                          </td>
                        ))}
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 4: 참여 현황 ── */}
        {tab === 4 && (
          <div style={{ background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001" }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 16 }}>연구원별 참여 현황</div>
            {memberStats.length === 0 ? <div style={{ textAlign: "center", color: "#ccc", padding: "40px 0" }}>연구원을 추가하세요</div> : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead><tr style={{ background: "#f7f8fa" }}>
                  {["이름", "고용형태", "직급", "참여 사업수", "최대 동시참여", "국비 참여율 합계", "총 인건비", "상태"].map(h => (
                    <th key={h} style={{ padding: "8px 10px", textAlign: "left", color: "#666", fontWeight: 600, borderBottom: "1px solid #eee", whiteSpace: "nowrap" }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {memberStats.map(m => {
                    const maxP = parseInt(m.maxProjects) || 5;
                    const maxR = parseFloat(m.maxRate) || 100;
                    const overProj = m.projCount > maxP;
                    const overRate = m.totalRate > maxR + 0.01;
                    const ok = !overProj && !overRate && m.projCount > 0;
                    return (
                      <tr key={m.id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                        <td style={{ padding: "8px 10px", fontWeight: 600 }}>{m.name}</td>
                        <td style={{ padding: "8px 10px" }}><span style={tag(EMP_COLOR[m.employType] + "22", EMP_COLOR[m.employType])}>{m.employType}</span></td>
                        <td style={{ padding: "8px 10px", color: "#555" }}>{m.rank}</td>
                        <td style={{ padding: "8px 10px", color: overProj ? "#e53935" : "#333", fontWeight: overProj ? 700 : 400 }}>{m.projCount}/{maxP}</td>
                        <td style={{ padding: "8px 10px", color: m.maxConcurrent > maxP ? "#e53935" : "#333" }}>{m.maxConcurrent}개</td>
                        <td style={{ padding: "8px 10px", color: overRate ? "#e53935" : "#333", fontWeight: overRate ? 700 : 400 }}>{m.totalRate.toFixed(2)}% / {maxR}%</td>
                        <td style={{ padding: "8px 10px" }}>₩{fmt(m.totalCost)}</td>
                        <td style={{ padding: "8px 10px" }}>
                          <span style={tag(ok ? "#e8f5e9" : m.projCount === 0 ? "#f5f5f5" : "#ffebee", ok ? "#2e7d32" : m.projCount === 0 ? "#aaa" : "#c62828")}>
                            {ok ? "정상" : m.projCount === 0 ? "미배분" : "초과"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* ── 연구원 모달 ── */}
      {showMem && (
        <Modal title={editMemId ? "연구원 수정" : "연구원 추가"} onClose={() => setShowMem(false)}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={{ gridColumn: "1/-1" }}>
              <label style={lbl}>이름 *</label>
              <input style={inp()} value={memF.name} onChange={e => setMemF(f => ({ ...f, name: e.target.value }))} placeholder="홍길동" />
            </div>
            <div>
              <label style={lbl}>고용형태</label>
              <select style={inp()} value={memF.employType} onChange={e => setMemF(f => ({ ...f, employType: e.target.value }))}>
                {EMPLOYMENT_TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}>직급</label>
              <select style={inp()} value={memF.rank} onChange={e => setMemF(f => ({ ...f, rank: e.target.value }))}>
                {RANKS.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
            <div style={{ gridColumn: "1/-1" }}>
              <label style={lbl}>월 인건비 (원) *</label>
              <input type="number" style={inp()} value={memF.salary} onChange={e => setMemF(f => ({ ...f, salary: e.target.value }))} placeholder="3000000" />
            </div>
            <div>
              <label style={lbl}>국비 참여율 상한 (%)</label>
              <input type="number" style={inp()} value={memF.maxRate} onChange={e => setMemF(f => ({ ...f, maxRate: e.target.value }))} placeholder="100" min="10" max="100" />
              <div style={{ fontSize: 11, color: "#aaa", marginTop: 3 }}>전체 국비 참여율 합계 기준</div>
            </div>
            <div>
              <label style={lbl}>최대 참여 사업 수</label>
              <input type="number" style={inp()} value={memF.maxProjects} onChange={e => setMemF(f => ({ ...f, maxProjects: e.target.value }))} placeholder="5" min="1" max="5" />
              <div style={{ fontSize: 11, color: "#aaa", marginTop: 3 }}>기본값 5개</div>
            </div>
            <div>
              <label style={lbl}>입사일</label>
              <input type="date" style={inp()} value={memF.hireDate} onChange={e => setMemF(f => ({ ...f, hireDate: e.target.value }))} />
            </div>
            <div>
              <label style={lbl}>퇴사(예정)일</label>
              <input type="date" style={inp()} value={memF.resignDate} onChange={e => setMemF(f => ({ ...f, resignDate: e.target.value }))} />
              <div style={{ fontSize: 11, color: "#e53935", marginTop: 3 }}>입력 시 해당 월 이후 사업 자동 제외</div>
            </div>
          </div>
          <SaveCancel onSave={saveMem} onClose={() => setShowMem(false)} />
        </Modal>
      )}

      {/* ── 사업 모달 ── */}
      {showProj && (
        <Modal title={editProjId ? "사업 수정" : "사업 추가"} onClose={() => setShowProj(false)}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
            <div style={{ gridColumn: "1/-1" }}>
              <label style={lbl}>사업명 *</label>
              <input style={inp()} value={projF.name} onChange={e => setProjF(f => ({ ...f, name: e.target.value }))} placeholder="사업명" />
            </div>
            <div>
              <label style={lbl}>시작일</label>
              <input type="date" style={inp()} value={projF.startDate} onChange={e => setProjF(f => ({ ...f, startDate: e.target.value, yearBudgets: {} }))} />
            </div>
            <div>
              <label style={lbl}>종료일</label>
              <input type="date" style={inp()} value={projF.endDate} onChange={e => setProjF(f => ({ ...f, endDate: e.target.value, yearBudgets: {} }))} />
            </div>
          </div>

          {/* 연도별 예산 */}
          {projYears.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <label style={{ ...lbl, marginBottom: 8 }}>연도별 인건비 총 예산 (원)</label>
              {projYears.map(yr => (
                <div key={yr} style={{ marginBottom: 10, background: "#f7f8fa", borderRadius: 8, padding: "10px 12px" }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: "#333" }}>{yr}년</div>
                  <input type="number" style={inp({ padding: "6px 8px", fontSize: 12 })} placeholder="0"
                    value={projF.yearBudgets?.[yr] ?? ""}
                    onChange={e => setProjF(f => ({ ...f, yearBudgets: { ...f.yearBudgets, [yr]: e.target.value } }))} />
                  <div style={{ fontSize: 11, color: "#aaa", marginTop: 4 }}>
                    고용형태별 배분은 자동 배분 실행 후 결과로 표시됩니다
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 필수 참여자 */}
          <div style={{ marginBottom: 14 }}>
            <label style={{ ...lbl, marginBottom: 8 }}>필수 참여자</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div>
                <label style={{ ...lbl, fontSize: 11 }}>연구책임자</label>
                <select style={inp()} value={projF.requiredMembers?.chief || ""} onChange={e => setProjF(f => ({ ...f, requiredMembers: { ...f.requiredMembers, chief: e.target.value } }))}>
                  <option value="">-- 선택 --</option>
                  {members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.rank})</option>)}
                </select>
              </div>
              <div>
                <label style={{ ...lbl, fontSize: 11 }}>실무자 (복수 선택)</label>
                <select multiple style={{ ...inp(), height: 80 }}
                  value={projF.requiredMembers?.staff || []}
                  onChange={e => setProjF(f => ({ ...f, requiredMembers: { ...f.requiredMembers, staff: Array.from(e.target.selectedOptions, o => o.value) } }))}>
                  {members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.rank})</option>)}
                </select>
                <div style={{ fontSize: 11, color: "#aaa", marginTop: 2 }}>Ctrl/Cmd 클릭으로 복수 선택</div>
              </div>
            </div>
          </div>

          {/* 연구원별 참여율 상한 */}
          {members.length > 0 && (
            <div style={{ marginBottom: 4 }}>
              <label style={{ ...lbl, marginBottom: 8 }}>연구원별 참여율 상한 (이 사업 한정)</label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {members.map(m => (
                  <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12, color: "#555", width: 70, whiteSpace: "nowrap", overflow: "hidden" }}>{m.name}</span>
                    <input type="number" style={inp({ padding: "5px 8px", fontSize: 12 })} placeholder="제한없음"
                      value={projF.memberConstraints?.[m.id]?.maxRate ?? ""}
                      onChange={e => setProjF(f => ({
                        ...f, memberConstraints: {
                          ...f.memberConstraints,
                          [m.id]: { ...f.memberConstraints?.[m.id], maxRate: e.target.value }
                        }
                      }))} />
                    <span style={{ fontSize: 11, color: "#aaa" }}>%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <SaveCancel onSave={saveProj} onClose={() => setShowProj(false)} />
        </Modal>
      )}
    </div>
  );
}
