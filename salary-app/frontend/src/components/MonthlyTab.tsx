import { useMemo } from "react";
import type { Member, Project, Participation } from "../api";
import { thS, tdS, btn } from "../ui/styles";
import { fmt, toM } from "../lib/format";
import { exportMonthlyExcel } from "../lib/excel";

export function MonthlyTab({
  members,
  projects,
  participations,
  distYear,
  setDistYear,
  selMember,
  setSelMember,
  allYears,
}: {
  members: Member[];
  projects: Project[];
  participations: Participation[];
  distYear: number;
  setDistYear: (y: number) => void;
  selMember: string | null;
  setSelMember: (id: string | null) => void;
  allYears: number[];
}) {
  const monthlyData = useMemo(() => {
    if (!selMember) return null;
    const member = members.find(m => m.id === selMember);
    if (!member) return null;
    const yrS = distYear * 12 + 1;
    const yrE = distYear * 12 + 12;
    const myParts = participations.filter(
      r => r.member_id === selMember && toM(r.end_date) >= yrS && toM(r.start_date) <= yrE,
    );
    const activeProjs = projects.filter(p => myParts.some(r => r.project_id === p.id));
    const monthData = Array.from({ length: 12 }, (_, i) => {
      const mi = yrS + i;
      const projRates: Record<string, number> = {};
      const projCosts: Record<string, number> = {};
      let totalRate = 0;
      let projCount = 0;
      for (const part of myParts) {
        if (toM(part.start_date) <= mi && mi <= toM(part.end_date)) {
          projRates[part.project_id] = part.rate;
          projCosts[part.project_id] = part.monthly_cost ?? 0; // SSOT: 백엔드 calc.py 값
          totalRate += part.rate;
          projCount++;
        }
      }
      return { mi, projRates, projCosts, totalRate, projCount };
    });
    return { member, activeProjs, monthData };
  }, [participations, members, projects, selMember, distYear]);

  const months = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];

  return (
    <div style={{ flex: 1, overflow: "hidden", background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001", display: "flex", flexDirection: "column" }}>
      <div style={{ flexShrink: 0, display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>연구원별 월별 참여율</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={() => exportMonthlyExcel(members, projects, participations, distYear)}
            disabled={participations.length === 0}
            style={btn("#e8f5e9", "#2e7d32", { opacity: participations.length === 0 ? 0.5 : 1 })}
            title={participations.length === 0 ? "자동 배분을 먼저 실행하세요" : `${distYear}년 전체 연구원 엑셀 다운로드`}
          >
            ⬇ 엑셀 다운로드
          </button>
          <select value={selMember ?? ""} onChange={e => setSelMember(e.target.value || null)}
            style={{ border: "1px solid #e0e0e0", borderRadius: 7, padding: "5px 10px", fontSize: 13, background: "#fafbfc", minWidth: 100 }}>
            <option value="">-- 연구원 선택 --</option>
            {members.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <select value={distYear} onChange={e => setDistYear(Number(e.target.value))}
            style={{ border: "1px solid #e0e0e0", borderRadius: 7, padding: "5px 10px", fontSize: 13, background: "#fafbfc" }}>
            {allYears.map(y => <option key={y} value={y}>{y}년</option>)}
          </select>
        </div>
      </div>
      {!monthlyData ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#ccc" }}>연구원을 선택하세요</div>
      ) : (
        (() => {
          const { member, activeProjs, monthData } = monthlyData;
          return (
            <div style={{ flex: 1, overflow: "auto" }}>
              <div style={{ marginBottom: 8, padding: "8px 12px", background: "#f0f3ff", borderRadius: 8, fontSize: 13, display: "flex", gap: 20 }}>
                <span style={{ fontWeight: 700 }}>{member.name}</span>
                <span style={{ color: "#555" }}>{member.employ_type} · {member.rank}</span>
                <span style={{ color: "#4f6ef7" }}>월 ₩{fmt(member.salary)}</span>
              </div>
              {activeProjs.length === 0 ? (
                <div style={{ padding: 20, color: "#ccc", textAlign: "center" }}>배분된 사업이 없습니다</div>
              ) : (
                <>
                  <div style={{ fontWeight: 600, fontSize: 13, color: "#333", margin: "12px 0 6px" }}>참여율 (%)</div>
                  <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: "100%", marginBottom: 20 }}>
                    <thead>
                      <tr>
                        <th style={{ ...thS, textAlign: "left", minWidth: 120 }}>사업명</th>
                        {months.map(m => <th key={m} style={{ ...thS, minWidth: 44 }}>{m}월</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {activeProjs.map(p => (
                        <tr key={p.id}>
                          <td style={{ ...tdS, textAlign: "left", fontWeight: 600 }}>{p.name}</td>
                          {monthData.map(({ mi, projRates }) => (
                            <td key={mi} style={{ ...tdS, color: projRates[p.id] ? "#4f6ef7" : "#ddd" }}>
                              {projRates[p.id] != null ? projRates[p.id].toFixed(1) : "-"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr style={{ background: "#f0f3ff" }}>
                        <td style={{ ...tdS, textAlign: "left", fontWeight: 700, color: "#4f6ef7" }}>합계</td>
                        {monthData.map(({ mi, totalRate }) => (
                          <td key={mi} style={{ ...tdS, fontWeight: 700, color: totalRate > 100 ? "#c62828" : "#4f6ef7" }}>
                            {totalRate > 0 ? totalRate.toFixed(1) : "-"}
                          </td>
                        ))}
                      </tr>
                    </tfoot>
                  </table>
                  <div style={{ fontWeight: 600, fontSize: 13, color: "#333", margin: "12px 0 6px" }}>인건비 (원)</div>
                  <table style={{ borderCollapse: "collapse", fontSize: 12, minWidth: "100%" }}>
                    <thead>
                      <tr>
                        <th style={{ ...thS, textAlign: "left", minWidth: 120 }}>사업명</th>
                        {months.map(m => <th key={m} style={{ ...thS, minWidth: 44 }}>{m}월</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {activeProjs.map(p => (
                        <tr key={p.id}>
                          <td style={{ ...tdS, textAlign: "left", fontWeight: 600 }}>{p.name}</td>
                          {monthData.map(({ mi, projCosts }) => (
                            <td key={mi} style={{ ...tdS, color: projCosts[p.id] ? "#333" : "#ddd" }}>
                              {projCosts[p.id] ? fmt(projCosts[p.id]) : "-"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr style={{ background: "#f7f8fa" }}>
                        <td style={{ ...tdS, textAlign: "left", fontWeight: 700, color: "#555" }}>참여사업개수</td>
                        {monthData.map(({ mi, projCount }) => (
                          <td key={mi} style={{ ...tdS, fontWeight: 600, color: projCount > 0 ? "#333" : "#ddd" }}>
                            {projCount > 0 ? projCount : "-"}
                          </td>
                        ))}
                      </tr>
                    </tfoot>
                  </table>
                </>
              )}
            </div>
          );
        })()
      )}
    </div>
  );
}
