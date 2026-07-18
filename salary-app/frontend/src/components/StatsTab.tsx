import type { MemberStat } from "../api";
import { tag, EMP_COLOR } from "../ui/styles";
import { fmt } from "../lib/format";

export function StatsTab({ stats }: { stats: MemberStat[] }) {
  return (
    <div style={{ flex: 1, overflow: "hidden", background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001", display: "flex", flexDirection: "column" }}>
      <div style={{ flexShrink: 0, fontWeight: 700, fontSize: 15, marginBottom: 16 }}>연구원별 참여 현황</div>
      {stats.length === 0 ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#ccc" }}>연구원을 추가하세요</div>
      ) : (
        <div style={{ flex: 1, overflow: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead style={{ position: "sticky", top: 0, zIndex: 1 }}>
              <tr style={{ background: "#f7f8fa" }}>
                {["이름", "고용형태", "직급", "참여 사업수", "최대 동시참여", "국비 참여율(월 최대)", "총 인건비", "상태"].map(h => (
                  <th key={h} style={{ padding: "8px 10px", textAlign: "left", color: "#666", fontWeight: 600, borderBottom: "1px solid #eee", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stats.map(m => (
                <tr key={m.member_id} style={{ borderBottom: "1px solid #f5f5f5" }}>
                  <td style={{ padding: "8px 10px", fontWeight: 600 }}>{m.member_name}</td>
                  <td style={{ padding: "8px 10px" }}><span style={tag(EMP_COLOR[m.employ_type] + "22", EMP_COLOR[m.employ_type])}>{m.employ_type}</span></td>
                  <td style={{ padding: "8px 10px", color: "#555" }}>{m.rank}</td>
                  <td style={{ padding: "8px 10px", color: "#333" }}>{m.proj_count}</td>
                  <td style={{ padding: "8px 10px", color: m.max_concurrent > m.max_projects ? "#e53935" : "#333", fontWeight: m.max_concurrent > m.max_projects ? 700 : 400 }}>{m.max_concurrent}/{m.max_projects}개</td>
                  <td style={{ padding: "8px 10px", color: m.total_rate > m.max_rate + 0.01 ? "#e53935" : "#333", fontWeight: m.total_rate > m.max_rate + 0.01 ? 700 : 400 }}>{m.total_rate.toFixed(2)}% / {m.max_rate}%</td>
                  <td style={{ padding: "8px 10px" }}>₩{fmt(m.total_cost)}</td>
                  <td style={{ padding: "8px 10px" }}>
                    <span style={tag(m.status === "정상" ? "#e8f5e9" : m.status === "미배분" ? "#f5f5f5" : "#ffebee", m.status === "정상" ? "#2e7d32" : m.status === "미배분" ? "#aaa" : "#c62828")}>
                      {m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
