import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, RefObject } from "react";
import type { Member, Project } from "../api";
import { updateMemberMonths, updateExclusions, reorderProjects } from "../api";
import { tag, btn } from "../ui/styles";
import { fmt, genProjMonths } from "../lib/format";

export function ProjectsTab({
  members,
  projects,
  selProj,
  setSelProj,
  loading,
  onAddProj,
  onEditProj,
  onDeleteProj,
  onDownloadTemplate,
  onCsvUpload,
  csvRef,
  onReload,
}: {
  members: Member[];
  projects: Project[];
  selProj: string | null;
  setSelProj: (id: string | null) => void;
  loading: boolean;
  onAddProj: () => void;
  onEditProj: (p: Project) => void;
  onDeleteProj: (id: string) => void;
  onDownloadTemplate: () => void;
  onCsvUpload: (e: ChangeEvent<HTMLInputElement>) => void;
  csvRef: RefObject<HTMLInputElement | null>;
  onReload: () => Promise<void> | void;
}) {
  /* 연구원별 강제 참여 월 / 제외 — 이 탭에서만 쓰는 로컬 상태 */
  const [memberMonthsLocal, setMemberMonthsLocal] = useState<Record<string, string[]>>({});
  const [excludedLocal, setExcludedLocal] = useState<string[]>([]);
  const [monthsDirty, setMonthsDirty] = useState(false);
  const [savingMonths, setSavingMonths] = useState(false);

  useEffect(() => {
    if (selProj) {
      const p = projects.find(pj => pj.id === selProj);
      setMemberMonthsLocal(p?.member_months ?? {});
      setExcludedLocal(p?.excluded_members ?? []);
      setMonthsDirty(false);
    }
  }, [selProj, projects]);

  const projMonths = useMemo(() => {
    const p = projects.find(pj => pj.id === selProj);
    if (!p) return [];
    const year = new Date().getFullYear();
    return genProjMonths(p.start_date, p.end_date).filter(ym => ym.startsWith(`${year}-`));
  }, [selProj, projects]);

  const projMonthYearGroups = useMemo(() => {
    const groups: { year: string; months: string[] }[] = [];
    projMonths.forEach(ym => {
      const year = ym.slice(0, 4);
      const last = groups[groups.length - 1];
      if (last && last.year === year) last.months.push(ym);
      else groups.push({ year, months: [ym] });
    });
    return groups;
  }, [projMonths]);

  const toggleMonth = (memberId: string, ym: string, checked: boolean) => {
    setMemberMonthsLocal(prev => {
      const cur = prev[memberId] ?? [];
      const next = checked ? [...cur, ym].sort() : cur.filter(m => m !== ym);
      return { ...prev, [memberId]: next };
    });
    setMonthsDirty(true);
  };

  const toggleAllMonths = (memberId: string, months: string[]) => {
    setMemberMonthsLocal(prev => ({ ...prev, [memberId]: months }));
    setMonthsDirty(true);
  };

  /* 제외 토글 (#3) — 제외 시 강제 참여 월은 비운다(상호 배타) */
  const toggleExcluded = (memberId: string, excluded: boolean) => {
    setExcludedLocal(prev => (excluded ? [...new Set([...prev, memberId])] : prev.filter(id => id !== memberId)));
    if (excluded) setMemberMonthsLocal(prev => ({ ...prev, [memberId]: [] }));
    setMonthsDirty(true);
  };

  const saveMonths = async () => {
    if (!selProj) return;
    setSavingMonths(true);
    try {
      await updateMemberMonths(selProj, memberMonthsLocal);
      await updateExclusions(selProj, excludedLocal);
      setMonthsDirty(false);
      await onReload();
    } finally {
      setSavingMonths(false);
    }
  };

  /* 예산 소진 우선순위 이동 (#2) — 위로 갈수록 먼저 배분 */
  const moveProject = async (idx: number, dir: -1 | 1) => {
    const j = idx + dir;
    if (j < 0 || j >= projects.length) return;
    const order = projects.map(p => p.id);
    [order[idx], order[j]] = [order[j], order[idx]];
    await reorderProjects(order);
    await onReload();
  };

  return (
    <div style={{ flex: 1, overflow: "hidden", display: "grid", gridTemplateColumns: "280px 1fr", gap: 12 }}>
      {/* 사업 목록 */}
      <div style={{ background: "#fff", borderRadius: 14, padding: 18, boxShadow: "0 1px 4px #0001", display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ flexShrink: 0, display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <span style={{ fontWeight: 700, fontSize: 14 }}>사업 목록 <span style={{ fontWeight: 400, fontSize: 10, color: "#aaa" }}>(위=예산 우선)</span></span>
          <div style={{ display: "flex", gap: 4 }}>
            <button onClick={onDownloadTemplate} style={btn("#f5f5f5", "#555", { fontSize: 11, padding: "4px 8px" })}>템플릿</button>
            <button onClick={() => csvRef.current?.click()} disabled={loading} style={btn("#e8f5e9", "#2e7d32", { fontSize: 11, padding: "4px 8px" })}>CSV</button>
            <input ref={csvRef} type="file" accept=".csv" style={{ display: "none" }} onChange={onCsvUpload} />
            <button onClick={onAddProj} style={btn("#4f6ef7", "#fff", { fontSize: 11, padding: "4px 10px" })}>+ 추가</button>
          </div>
        </div>
        <div style={{ flex: 1, overflowY: "auto" }}>
          {projects.length === 0 && <div style={{ color: "#ccc", fontSize: 13, textAlign: "center", padding: 20 }}>사업을 추가하세요</div>}
          {projects.map((p, idx) => {
            const totalBudget = Object.values(p.year_budgets).reduce((s, v) => s + (v || 0), 0);
            const orderBtn = (dir: -1 | 1, disabled: boolean, label: string) => (
              <button onClick={e => { e.stopPropagation(); moveProject(idx, dir); }} disabled={disabled}
                title={dir === -1 ? "우선순위 올리기" : "우선순위 내리기"}
                style={{ border: "1px solid #e3e3e3", background: "#fff", borderRadius: 5, width: 20, height: 18, fontSize: 9, lineHeight: 1, cursor: disabled ? "default" : "pointer", color: disabled ? "#ddd" : "#888", padding: 0 }}>
                {label}
              </button>
            );
            return (
              <div key={p.id} onClick={() => setSelProj(p.id)} style={{ display: "flex", alignItems: "center", gap: 6, borderRadius: 9, padding: "10px 12px", marginBottom: 7, cursor: "pointer", border: "1.5px solid", borderColor: selProj === p.id ? "#4f6ef7" : "#eee", background: selProj === p.id ? "#f0f3ff" : "#fafafa" }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: "#bbb", minWidth: 14 }}>{idx + 1}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{p.name}</div>
                  <div style={{ fontSize: 11, color: "#aaa" }}>{p.start_date} ~ {p.end_date}</div>
                  <div style={{ fontSize: 11, color: "#4f6ef7", fontWeight: 600, marginTop: 2 }}>총 ₩{fmt(totalBudget)}</div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {orderBtn(-1, idx === 0, "▲")}
                  {orderBtn(1, idx === projects.length - 1, "▼")}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 사업 상세 */}
      <div style={{ background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001", overflowY: "auto" }}>
        {!selProj ? (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "#ccc" }}>사업을 선택하세요</div>
        ) : (
          (() => {
            const p = projects.find(pj => pj.id === selProj);
            if (!p) return null;
            const chief = members.find(m => m.id === p.required_members?.chief);
            const staffList = (p.required_members?.staff || []).map(id => members.find(m => m.id === id)).filter(Boolean) as Member[];
            return (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                  <div>
                    <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{p.name}</h2>
                    <div style={{ fontSize: 12, color: "#aaa", marginTop: 3 }}>{p.start_date} ~ {p.end_date}</div>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button onClick={() => onEditProj(p)} style={btn("#f0f3ff", "#4f6ef7")}>수정</button>
                    <button onClick={() => onDeleteProj(p.id)} style={btn("#fff0f0", "#e53935")}>삭제</button>
                  </div>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: "#333" }}>연도별 인건비 예산</div>
                  {Object.entries(p.year_budgets).map(([yr, total]) => (
                    <div key={yr} style={{ background: "#f7f8fa", borderRadius: 8, padding: "8px 12px", marginBottom: 6, fontSize: 13 }}>
                      <span style={{ fontWeight: 600, marginRight: 12 }}>{yr}년</span>
                      <span style={{ color: "#4f6ef7", fontWeight: 600 }}>₩{fmt(total)}</span>
                    </div>
                  ))}
                </div>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: "#333" }}>필수 참여자</div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    {chief && <span style={tag("#4f6ef722", "#4f6ef7")}>연구책임자: {chief.name}</span>}
                    {staffList.map(m => <span key={m.id} style={tag("#26a69a22", "#26a69a")}>실무자: {m.name}</span>)}
                    {!chief && staffList.length === 0 && <span style={{ color: "#ccc", fontSize: 13 }}>미지정</span>}
                  </div>
                </div>
                {Object.keys(p.member_constraints || {}).length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: "#333" }}>연구원별 참여율 상한</div>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      {Object.entries(p.member_constraints).map(([mid, c]) => {
                        const m = members.find(m => m.id === mid);
                        return m ? <span key={mid} style={tag("#ff980022", "#e65100")}>{m.name}: 최대 {c.max_rate}%</span> : null;
                      })}
                    </div>
                  </div>
                )}
                {projMonths.length > 0 && (
                  <div style={{ borderTop: "1px solid #f0f0f0", paddingTop: 16 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                      <div>
                        <span style={{ fontWeight: 700, fontSize: 13, color: "#333" }}>연구원별 참여 월 설정</span>
                        <span style={{ fontSize: 11, color: "#aaa", marginLeft: 8 }}>월 선택 = 강제 배분(슬롯 차지) · 제외 = 배분 안 함 · 미선택 = 자동 배분 대상</span>
                      </div>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        {monthsDirty && <span style={{ fontSize: 11, color: "#e53935" }}>미저장</span>}
                        <button onClick={saveMonths} disabled={savingMonths || !monthsDirty}
                          style={btn("#4f6ef7", "#fff", { fontSize: 11, padding: "4px 12px", opacity: !monthsDirty || savingMonths ? 0.5 : 1 })}>
                          {savingMonths ? "저장중..." : "저장"}
                        </button>
                      </div>
                    </div>
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ borderCollapse: "collapse", fontSize: 11, minWidth: "100%" }}>
                        <thead>
                          <tr>
                            <th style={{ padding: "4px 8px", textAlign: "left", borderBottom: "1px solid #eee", whiteSpace: "nowrap", minWidth: 70, color: "#555", fontWeight: 600 }}>연구원</th>
                            {projMonthYearGroups.map(({ year, months }) => (
                              <th key={year} colSpan={months.length} style={{ padding: "4px 0", textAlign: "center", borderBottom: "1px solid #eee", color: "#4f6ef7", fontWeight: 700, borderLeft: "2px solid #e8ecff" }}>{year}년</th>
                            ))}
                          </tr>
                          <tr>
                            <th style={{ padding: "3px 8px", borderBottom: "2px solid #eee" }}></th>
                            {projMonths.map((ym, i) => {
                              const isYearStart = i === 0 || ym.slice(5) === "01";
                              return (
                                <th key={ym} style={{ padding: "3px 2px", textAlign: "center", borderBottom: "2px solid #eee", color: "#888", fontWeight: 400, borderLeft: isYearStart ? "2px solid #e8ecff" : "none" }}>
                                  {parseInt(ym.slice(5))}
                                </th>
                              );
                            })}
                          </tr>
                        </thead>
                        <tbody>
                          {members.map(m => {
                            const checkedMonths = memberMonthsLocal[m.id] ?? [];
                            const noneChecked = checkedMonths.length === 0;
                            const isResigned = !!m.resign_date && new Date(m.resign_date) < new Date();
                            const resignYm = m.resign_date ? m.resign_date.slice(0, 7) : null;
                            const availMonths = resignYm ? projMonths.filter(ym => ym <= resignYm) : projMonths;
                            const isExcluded = excludedLocal.includes(m.id);
                            const allChecked = availMonths.length > 0 && availMonths.every(ym => checkedMonths.includes(ym));
                            return (
                              <tr key={m.id} style={{ borderBottom: "1px solid #f5f5f5", opacity: isResigned ? 0.45 : 1 }}>
                                <td style={{ padding: "4px 8px", whiteSpace: "nowrap" }}>
                                  <label title="이 사업에서 제외" style={{ display: "inline-flex", alignItems: "center", gap: 2, fontSize: 10, color: isExcluded ? "#e53935" : "#bbb", cursor: "pointer", marginRight: 6, userSelect: "none" }}>
                                    <input type="checkbox" checked={isExcluded} onChange={e => toggleExcluded(m.id, e.target.checked)} style={{ accentColor: "#e53935", cursor: "pointer" }} />제외
                                  </label>
                                  <label title="당해 모든 기간 참여" style={{ display: "inline-flex", alignItems: "center", gap: 2, fontSize: 10, color: isExcluded ? "#ddd" : allChecked ? "#4f6ef7" : "#bbb", cursor: isExcluded || availMonths.length === 0 ? "default" : "pointer", marginRight: 6, userSelect: "none" }}>
                                    <input type="checkbox" checked={allChecked} disabled={isExcluded || availMonths.length === 0} onChange={e => toggleAllMonths(m.id, e.target.checked ? availMonths : [])} style={{ accentColor: "#4f6ef7", cursor: isExcluded ? "default" : "pointer" }} />전체
                                  </label>
                                  <span style={{ fontWeight: 600, color: isExcluded ? "#bbb" : "#333", textDecoration: isExcluded ? "line-through" : "none" }}>{m.name}</span>
                                  {!noneChecked && !isExcluded && <span style={{ ...tag("#e8f0ff", "#4f6ef7"), marginLeft: 4 }}>{checkedMonths.length}개월</span>}
                                </td>
                                {projMonths.map((ym, i) => {
                                  const isYearStart = i === 0 || ym.slice(5) === "01";
                                  const isDisabled = resignYm ? ym > resignYm : false;
                                  return (
                                    <td key={ym} style={{ padding: "4px 2px", textAlign: "center", borderLeft: isYearStart ? "2px solid #e8ecff" : "none" }}>
                                      <input type="checkbox" checked={checkedMonths.includes(ym) && !isExcluded} disabled={isDisabled || isExcluded}
                                        onChange={e => toggleMonth(m.id, ym, e.target.checked)}
                                        style={{ cursor: isDisabled || isExcluded ? "default" : "pointer", accentColor: "#4f6ef7" }} />
                                    </td>
                                  );
                                })}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            );
          })()
        )}
      </div>
    </div>
  );
}
