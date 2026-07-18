import { useMemo } from "react";
import type { Member, Project, Participation, BudgetStatus } from "../api";
import { thS, tdS, btn, tag } from "../ui/styles";
import { fmt, toM } from "../lib/format";

export function SummaryTab({
  members,
  projects,
  participations,
  budgetStatus,
  distYear,
  setDistYear,
  allYears,
  loading,
  onRedistribute,
  onSelectMember,
}: {
  members: Member[];
  projects: Project[];
  participations: Participation[];
  budgetStatus: BudgetStatus[];
  distYear: number;
  setDistYear: (y: number) => void;
  allYears: number[];
  loading: boolean;
  onRedistribute: () => void;
  onSelectMember: (id: string) => void;
}) {
  const underfilled = budgetStatus.filter(b => b.reason === "saturated" || b.reason === "slack");
  const { activeProjs, memberRows, projStats } = useMemo(() => {
    const yrS = distYear * 12 + 1;
    const yrE = distYear * 12 + 12;
    const activeProjs = projects.filter(
      p => p.start_date && p.end_date && toM(p.end_date) >= yrS && toM(p.start_date) <= yrE,
    );
    const memberRows = members
      .map(m => {
        const myParts = participations.filter(r => r.member_id === m.id);
        const projCosts: Record<string, number> = {};
        let totalCost = 0;
        for (const p of activeProjs) {
          // 한 연구원이 한 사업에 연도·기간별 여러 세그먼트를 가질 수 있다 → 해당 연도에 걸친 분량을 모두 합산
          let cost = 0;
          for (const part of myParts) {
            if (part.project_id !== p.id) continue;
            const months = Math.max(0, Math.min(toM(part.end_date), yrE) - Math.max(toM(part.start_date), yrS) + 1);
            if (months > 0) cost += (part.monthly_cost ?? 0) * months; // SSOT: 백엔드 calc.py 값
          }
          projCosts[p.id] = cost;
          totalCost += cost;
        }
        // 종참여율 = 그 해 월별 동시 참여율 합의 피크 (세그먼트가 기간별로 나뉘어도 정확)
        let peakRate = 0;
        for (let mi = yrS; mi <= yrE; mi++) {
          const sum = myParts
            .filter(r => toM(r.start_date) <= mi && mi <= toM(r.end_date))
            .reduce((a, r) => a + r.rate, 0);
          peakRate = Math.max(peakRate, sum);
        }
        return { member: m, projCosts, totalCost, peakRate };
      })
      .filter(r => Object.values(r.projCosts).some(c => c > 0));

    const projStats: Record<string, { budget: number; allocated: number }> = {};
    for (const p of activeProjs) {
      const budget = p.year_budgets[String(distYear)] ?? 0;
      const allocated = memberRows.reduce((s, r) => s + (r.projCosts[p.id] ?? 0), 0);
      projStats[p.id] = { budget, allocated };
    }
    return { activeProjs, memberRows, projStats };
  }, [participations, projects, members, distYear]);

  return (
    <div style={{ flex: 1, overflow: "hidden", background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001", display: "flex", flexDirection: "column" }}>
      <div style={{ flexShrink: 0, display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>사업별 인건비 총괄표</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <select value={distYear} onChange={e => setDistYear(Number(e.target.value))}
            style={{ border: "1px solid #e0e0e0", borderRadius: 7, padding: "5px 10px", fontSize: 13, background: "#fafbfc" }}>
            {allYears.map(y => <option key={y} value={y}>{y}년</option>)}
          </select>
          <button onClick={onRedistribute} disabled={loading} style={btn("#4f6ef7", "#fff")}>⚡ 재배분</button>
        </div>
      </div>
      {activeProjs.length === 0 ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#ccc" }}>해당 연도에 진행 중인 사업이 없습니다</div>
      ) : (
        <div style={{ flex: 1, overflow: "auto" }}>
          <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: "100%" }}>
            <thead>
              <tr>
                <th style={{ ...thS, textAlign: "left", minWidth: 80 }}>연구원</th>
                {activeProjs.map(p => <th key={p.id} style={{ ...thS, minWidth: 100 }}>{p.name}</th>)}
                <th style={{ ...thS, minWidth: 90, background: "#f0f3ff", color: "#4f6ef7" }}>인건비합계</th>
                <th style={{ ...thS, minWidth: 70, background: "#f0f3ff", color: "#4f6ef7" }}>종참여율</th>
              </tr>
              <tr>
                <th style={{ ...thS, textAlign: "left", color: "#aaa", fontWeight: 400 }}>재원</th>
                {activeProjs.map(p => <th key={p.id} style={{ ...thS, color: "#aaa", fontWeight: 400 }}>국비</th>)}
                <th style={{ ...thS, background: "#f0f3ff" }}></th>
                <th style={{ ...thS, background: "#f0f3ff" }}></th>
              </tr>
              <tr>
                <th style={{ ...thS, textAlign: "left", color: "#aaa", fontWeight: 400 }}>사업기간</th>
                {activeProjs.map(p => <th key={p.id} style={{ ...thS, color: "#aaa", fontWeight: 400, fontSize: 10 }}>{p.start_date.slice(0, 7)}~{p.end_date.slice(0, 7)}</th>)}
                <th style={{ ...thS, background: "#f0f3ff" }}></th>
                <th style={{ ...thS, background: "#f0f3ff" }}></th>
              </tr>
              <tr>
                <th style={{ ...thS, textAlign: "left", color: "#aaa", fontWeight: 400 }}>{distYear}년 예산</th>
                {activeProjs.map(p => <th key={p.id} style={{ ...thS, color: "#333" }}>₩{fmt(projStats[p.id]?.budget)}</th>)}
                <th style={{ ...thS, background: "#f0f3ff" }}></th>
                <th style={{ ...thS, background: "#f0f3ff" }}></th>
              </tr>
            </thead>
            <tbody>
              {memberRows.map(({ member: m, projCosts, totalCost, peakRate }) => (
                <tr key={m.id} onClick={() => onSelectMember(m.id)} style={{ cursor: "pointer" }}
                  onMouseEnter={e => (e.currentTarget.style.background = "#f5f7ff")}
                  onMouseLeave={e => (e.currentTarget.style.background = "")}>
                  <td style={{ ...tdS, textAlign: "left", fontWeight: 600 }}>{m.name}</td>
                  {activeProjs.map(p => (
                    <td key={p.id} style={{ ...tdS, color: projCosts[p.id] ? "#333" : "#ccc" }}>
                      {projCosts[p.id] ? `₩${fmt(projCosts[p.id])}` : "-"}
                    </td>
                  ))}
                  <td style={{ ...tdS, fontWeight: 700, color: "#4f6ef7", background: "#f8f9ff" }}>₩{fmt(totalCost)}</td>
                  <td style={{ ...tdS, fontWeight: 600, color: "#26a69a", background: "#f8f9ff" }}>{peakRate.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td style={{ ...tdS, textAlign: "left", fontWeight: 700, background: "#e8f5e9", color: "#2e7d32" }}>배정된금액</td>
                {activeProjs.map(p => (
                  <td key={p.id} style={{ ...tdS, fontWeight: 700, background: "#e8f5e9", color: "#2e7d32" }}>₩{fmt(projStats[p.id]?.allocated)}</td>
                ))}
                <td style={{ ...tdS, background: "#e8f5e9" }}></td>
                <td style={{ ...tdS, background: "#e8f5e9" }}></td>
              </tr>
              <tr>
                <td style={{ ...tdS, textAlign: "left", fontWeight: 700, background: "#fff3e0", color: "#e65100" }}>잔액</td>
                {activeProjs.map(p => {
                  const { budget, allocated } = projStats[p.id] ?? { budget: 0, allocated: 0 };
                  const residual = budget - allocated;
                  return (
                    <td key={p.id} style={{ ...tdS, fontWeight: 700, background: "#fff3e0", color: residual < 0 ? "#c62828" : residual === 0 ? "#2e7d32" : "#e65100" }}>
                      ₩{fmt(residual)}
                    </td>
                  );
                })}
                <td style={{ ...tdS, background: "#fff3e0" }}></td>
                <td style={{ ...tdS, background: "#fff3e0" }}></td>
              </tr>
            </tfoot>
          </table>

          {underfilled.length > 0 && (
            <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px dashed #eee" }}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: "#e65100" }}>
                ⚠ 예산 미소진 사유 <span style={{ fontWeight: 400, color: "#aaa" }}>(전체 기간 기준)</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {underfilled.map(b => (
                  <div key={b.project_id} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, flexWrap: "wrap" }}>
                    <span style={{ minWidth: 150, fontWeight: 600 }}>{b.project_name}</span>
                    <span style={{ color: "#c62828", minWidth: 110 }}>잔액 ₩{fmt(b.remaining)}</span>
                    <span style={tag(b.reason === "slack" ? "#fff8e1" : "#ffebee", b.reason === "slack" ? "#e65100" : "#c62828")}>
                      {b.reason === "slack" ? "추가 여력" : "인력 포화"}
                    </span>
                    <span style={{ color: "#666" }}>{b.detail}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
