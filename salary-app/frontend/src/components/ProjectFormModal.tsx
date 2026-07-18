import type { Dispatch, SetStateAction } from "react";
import type { Member, Project } from "../api";
import { Modal, SaveCancel } from "../ui/Modal";
import { lbl, inp } from "../ui/styles";

type ProjectForm = Omit<Project, "id">;

export function ProjectFormModal({
  form,
  setForm,
  editing,
  members,
  projYears,
  onSave,
  onClose,
}: {
  form: ProjectForm;
  setForm: Dispatch<SetStateAction<ProjectForm>>;
  editing: boolean;
  members: Member[];
  projYears: number[];
  onSave: () => void;
  onClose: () => void;
}) {
  return (
    <Modal title={editing ? "사업 수정" : "사업 추가"} onClose={onClose}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 14 }}>
        <div style={{ gridColumn: "1/-1" }}>
          <label style={lbl}>사업명 *</label>
          <input style={inp()} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="사업명" />
        </div>
        <div>
          <label style={lbl}>시작일</label>
          <input type="date" style={inp()} value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value, year_budgets: {} }))} />
        </div>
        <div>
          <label style={lbl}>종료일</label>
          <input type="date" style={inp()} value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value, year_budgets: {} }))} />
        </div>
      </div>
      {projYears.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <label style={{ ...lbl, marginBottom: 8 }}>연도별 인건비 예산 (원)</label>
          {projYears.map(yr => (
            <div key={yr} style={{ marginBottom: 10, background: "#f7f8fa", borderRadius: 8, padding: "10px 12px" }}>
              <label style={{ ...lbl, fontSize: 12, marginBottom: 4 }}>{yr}년 인건비 예산 (원)</label>
              <input type="number" style={inp({ padding: "7px 10px", fontSize: 13 })} placeholder="0"
                value={form.year_budgets?.[yr] ?? ""}
                onChange={e => setForm(f => ({ ...f, year_budgets: { ...f.year_budgets, [yr]: Number(e.target.value) } }))} />
            </div>
          ))}
        </div>
      )}
      <div style={{ marginBottom: 14 }}>
        <label style={{ ...lbl, marginBottom: 8 }}>필수 참여자</label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div>
            <label style={{ ...lbl, fontSize: 11 }}>연구책임자</label>
            <select style={inp()} value={form.required_members?.chief || ""} onChange={e => setForm(f => ({ ...f, required_members: { ...f.required_members, chief: e.target.value || null } }))}>
              <option value="">-- 선택 --</option>
              {members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.rank})</option>)}
            </select>
          </div>
          <div>
            <label style={{ ...lbl, fontSize: 11 }}>실무자 (복수 선택)</label>
            <select multiple style={{ ...inp(), height: 80 }}
              value={form.required_members?.staff || []}
              onChange={e => setForm(f => ({ ...f, required_members: { ...f.required_members, staff: Array.from(e.target.selectedOptions, o => o.value) } }))}>
              {members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.rank})</option>)}
            </select>
            <div style={{ fontSize: 11, color: "#aaa", marginTop: 2 }}>Ctrl/Cmd 클릭으로 복수 선택</div>
          </div>
        </div>
      </div>
      {members.length > 0 && (
        <div style={{ marginBottom: 4 }}>
          <label style={{ ...lbl, marginBottom: 8 }}>연구원별 참여율 상한 (이 사업 한정)</label>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {members.map(m => (
              <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 12, color: "#555", width: 70, whiteSpace: "nowrap", overflow: "hidden" }}>{m.name}</span>
                <input type="number" style={inp({ padding: "5px 8px", fontSize: 12 })} placeholder="제한없음"
                  value={form.member_constraints?.[m.id]?.max_rate ?? ""}
                  onChange={e => {
                    const val = e.target.value;
                    setForm(f => {
                      const next = { ...f.member_constraints };
                      if (val) next[m.id] = { max_rate: Number(val) };
                      else delete next[m.id];
                      return { ...f, member_constraints: next };
                    });
                  }} />
                <span style={{ fontSize: 11, color: "#aaa" }}>%</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <SaveCancel onSave={onSave} onClose={onClose} />
    </Modal>
  );
}
