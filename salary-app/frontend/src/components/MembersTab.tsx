import type { ChangeEvent, RefObject } from "react";
import type { Member } from "../api";
import { tag, btn, EMP_COLOR } from "../ui/styles";
import { fmt } from "../lib/format";

export function MembersTab({
  members,
  loading,
  onAdd,
  onEdit,
  onDelete,
  onCsvUpload,
  onDownloadTemplate,
  csvRef,
}: {
  members: Member[];
  loading: boolean;
  onAdd: () => void;
  onEdit: (m: Member) => void;
  onDelete: (id: string) => void;
  onCsvUpload: (e: ChangeEvent<HTMLInputElement>) => void;
  onDownloadTemplate: () => void;
  csvRef: RefObject<HTMLInputElement | null>;
}) {
  return (
    <div style={{ flex: 1, overflow: "hidden", background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 1px 4px #0001", display: "flex", flexDirection: "column" }}>
      <div style={{ flexShrink: 0, display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>전체 연구원 ({members.length}명)</span>
        <div style={{ display: "flex", gap: 6 }}>
          <button onClick={onDownloadTemplate} style={btn("#f5f5f5", "#555")}>템플릿 다운로드</button>
          <button onClick={() => csvRef.current?.click()} disabled={loading} style={btn("#e8f5e9", "#2e7d32")}>CSV 업로드</button>
          <input ref={csvRef} type="file" accept=".csv" style={{ display: "none" }} onChange={onCsvUpload} />
          <button onClick={onAdd} style={btn("#4f6ef7", "#fff")}>+ 연구원 추가</button>
        </div>
      </div>
      {members.length === 0 ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#ccc" }}>연구원을 추가하세요</div>
      ) : (
        <div style={{ flex: 1, overflow: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead style={{ position: "sticky", top: 0, zIndex: 1 }}>
              <tr style={{ background: "#f7f8fa" }}>
                {["이름", "국가연구자번호", "고용형태", "직급", "생년월일", "재직기간", "월 인건비", "국비 참여율 상한", "최대 참여 사업수", ""].map(h => (
                  <th key={h} style={{ padding: "8px 10px", textAlign: "left", color: "#666", fontWeight: 600, borderBottom: "1px solid #eee", whiteSpace: "nowrap" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {members.map(m => {
                const today = new Date();
                const resigned = !!m.resign_date && new Date(m.resign_date) < today;
                return (
                  <tr key={m.id} style={{ borderBottom: "1px solid #f5f5f5", opacity: resigned ? 0.55 : 1 }}>
                    <td style={{ padding: "9px 10px", fontWeight: 600 }}>
                      {m.name}
                      {resigned && <span style={{ ...tag("#ffebee", "#c62828"), marginLeft: 5 }}>퇴사</span>}
                    </td>
                    <td style={{ padding: "9px 10px", fontSize: 12, color: "#555", fontFamily: "monospace" }}>{m.researcher_no ?? <span style={{ color: "#ccc" }}>미등록</span>}</td>
                    <td style={{ padding: "9px 10px" }}><span style={tag(EMP_COLOR[m.employ_type] + "22", EMP_COLOR[m.employ_type])}>{m.employ_type}</span></td>
                    <td style={{ padding: "9px 10px", color: "#555" }}>{m.rank}</td>
                    <td style={{ padding: "9px 10px", fontSize: 12, color: "#777" }}>{m.birth_date ?? <span style={{ color: "#ccc" }}>미등록</span>}</td>
                    <td style={{ padding: "9px 10px", fontSize: 11, color: "#777", whiteSpace: "nowrap" }}>
                      {!m.hire_date && !m.resign_date ? (
                        <span style={{ color: "#ccc" }}>미설정</span>
                      ) : (
                        <span>
                          {m.hire_date ?? "-"}
                          {" ~ "}
                          {m.resign_date ? (
                            <span style={{ color: "#e53935", fontWeight: 600 }}>{m.resign_date}</span>
                          ) : (
                            <span style={{ color: "#aaa" }}>재직중</span>
                          )}
                        </span>
                      )}
                    </td>
                    <td style={{ padding: "9px 10px" }}>₩{fmt(m.salary)}</td>
                    <td style={{ padding: "9px 10px", color: m.max_rate < 100 ? "#e53935" : "#333", fontWeight: m.max_rate < 100 ? 700 : 400 }}>{m.max_rate}%</td>
                    <td style={{ padding: "9px 10px", color: m.max_projects < 5 ? "#e53935" : "#333", fontWeight: m.max_projects < 5 ? 700 : 400 }}>{m.max_projects}개</td>
                    <td style={{ padding: "9px 10px" }}>
                      <div style={{ display: "flex", gap: 5 }}>
                        <button onClick={() => onEdit(m)} style={btn("#f0f3ff", "#4f6ef7")}>수정</button>
                        <button onClick={() => onDelete(m.id)} style={btn("#fff0f0", "#e53935")}>삭제</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
