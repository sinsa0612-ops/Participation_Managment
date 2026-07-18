import { useState } from "react";
import type { Participation, Override } from "../api";
import { tag, btn, ROLE_COLOR, EMP_COLOR } from "../ui/styles";
import { fmt } from "../lib/format";

const key = (projectId: string, memberId: string) => `${projectId}|${memberId}`;

export function DistributionTab({
  participations,
  overrides,
  loading,
  onRedistribute,
  onSetOverride,
  onClearOverride,
}: {
  participations: Participation[];
  overrides: Override[];
  loading: boolean;
  onRedistribute: () => void;
  onSetOverride: (projectId: string, memberId: string, rate: number) => void;
  onClearOverride: (projectId: string, memberId: string) => void;
}) {
  const [edits, setEdits] = useState<Record<string, string>>({});
  const overridden = new Set(overrides.map(o => key(o.project_id, o.member_id)));

  return (
    <div style={{ flex: 1, overflow: "hidden", background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001", display: "flex", flexDirection: "column" }}>
      <div style={{ flexShrink: 0, display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>
          배분 결과 ({participations.length}건)
          <span style={{ fontWeight: 400, fontSize: 11, color: "#aaa", marginLeft: 8 }}>참여율을 직접 수정 후 💾 저장 — 재배분해도 유지됩니다</span>
        </span>
        <button onClick={onRedistribute} disabled={loading} style={btn("#4f6ef7", "#fff")}>⚡ 재배분</button>
      </div>
      {participations.length === 0 ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#ccc" }}>자동 배분을 실행하세요</div>
      ) : (
        <div style={{ flex: 1, overflow: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead style={{ position: "sticky", top: 0, zIndex: 1 }}>
              <tr style={{ background: "#f7f8fa" }}>
                {["사업명", "연구원", "고용형태", "역할", "참여기간", "개월", "참여율(수정 가능)", "인건비"].map(h => (
                  <th key={h} style={{ padding: "8px 10px", textAlign: "left", color: "#666", fontWeight: 600, borderBottom: "1px solid #eee", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {participations.map((r, i) => {
                const k = key(r.project_id, r.member_id);
                const isOverridden = overridden.has(k);
                const editVal = edits[k] ?? String(r.rate);
                return (
                  <tr key={i} style={{ borderBottom: "1px solid #f5f5f5" }}>
                    <td style={{ padding: "8px 10px", fontWeight: 600, color: "#1a1a2e" }}>{r.proj_name}</td>
                    <td style={{ padding: "8px 10px" }}>{r.member_name} <span style={{ color: "#aaa", fontSize: 11 }}>{r.rank}</span></td>
                    <td style={{ padding: "8px 10px" }}><span style={tag(EMP_COLOR[r.employ_type ?? ""] + "22", EMP_COLOR[r.employ_type ?? ""])}>{r.employ_type}</span></td>
                    <td style={{ padding: "8px 10px" }}><span style={tag(ROLE_COLOR[r.role] + "33", ROLE_COLOR[r.role])}>{r.role}</span></td>
                    <td style={{ padding: "8px 10px", color: "#777", whiteSpace: "nowrap", fontSize: 12 }}>{r.start_date} ~ {r.end_date}</td>
                    <td style={{ padding: "8px 10px", color: "#555" }}>{r.months}개월</td>
                    <td style={{ padding: "8px 10px", whiteSpace: "nowrap" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <input
                          type="number" min={0} max={100} step={0.01} value={editVal} disabled={loading}
                          onChange={e => setEdits(s => ({ ...s, [k]: e.target.value }))}
                          style={{ width: 64, border: "1px solid #e0e0e0", borderRadius: 6, padding: "3px 6px", fontSize: 12, textAlign: "right", color: isOverridden ? "#e65100" : "#4f6ef7", fontWeight: 600 }}
                        />
                        <span style={{ fontSize: 11, color: "#aaa" }}>%</span>
                        <button title="이 참여율로 고정 저장" disabled={loading}
                          onClick={() => { onSetOverride(r.project_id, r.member_id, Number(editVal)); setEdits(s => { const n = { ...s }; delete n[k]; return n; }); }}
                          style={btn("#e8f5e9", "#2e7d32", { fontSize: 11, padding: "3px 7px" })}>💾</button>
                        {isOverridden && (
                          <button title="자동 계산값으로 되돌리기" disabled={loading}
                            onClick={() => { onClearOverride(r.project_id, r.member_id); setEdits(s => { const n = { ...s }; delete n[k]; return n; }); }}
                            style={btn("#fff3e0", "#e65100", { fontSize: 11, padding: "3px 7px" })}>↺</button>
                        )}
                        {isOverridden && <span style={{ ...tag("#fff3e0", "#e65100"), marginLeft: 2 }}>수동</span>}
                      </div>
                    </td>
                    <td style={{ padding: "8px 10px", fontWeight: 600 }}>₩{fmt(r.cost)}</td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr style={{ background: "#f0f3ff" }}>
                <td colSpan={7} style={{ padding: "9px 10px", fontWeight: 700 }}>합계</td>
                <td style={{ padding: "9px 10px", fontWeight: 700, color: "#4f6ef7" }}>₩{fmt(participations.reduce((s, r) => s + r.cost, 0))}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}
