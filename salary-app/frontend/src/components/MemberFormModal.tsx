import type { Dispatch, SetStateAction } from "react";
import type { Member } from "../api";
import { Modal, SaveCancel } from "../ui/Modal";
import { EMPLOYMENT_TYPES, RANKS, lbl, inp } from "../ui/styles";

type MemberForm = Omit<Member, "id">;

export function MemberFormModal({
  form,
  setForm,
  editing,
  onSave,
  onClose,
}: {
  form: MemberForm;
  setForm: Dispatch<SetStateAction<MemberForm>>;
  editing: boolean;
  onSave: () => void;
  onClose: () => void;
}) {
  return (
    <Modal title={editing ? "연구원 수정" : "연구원 추가"} onClose={onClose}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={{ gridColumn: "1/-1" }}>
          <label style={lbl}>이름 *</label>
          <input style={inp()} value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="홍길동" />
        </div>
        <div>
          <label style={lbl}>고용형태</label>
          <select style={inp()} value={form.employ_type} onChange={e => setForm(f => ({ ...f, employ_type: e.target.value as (typeof EMPLOYMENT_TYPES)[number] }))}>
            {EMPLOYMENT_TYPES.map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label style={lbl}>직급</label>
          <select style={inp()} value={form.rank} onChange={e => setForm(f => ({ ...f, rank: e.target.value as (typeof RANKS)[number] }))}>
            {RANKS.map(r => <option key={r}>{r}</option>)}
          </select>
        </div>
        <div style={{ gridColumn: "1/-1" }}>
          <label style={lbl}>월 인건비 (원) *</label>
          <input type="number" style={inp()} value={form.salary || ""} onChange={e => setForm(f => ({ ...f, salary: Number(e.target.value) }))} placeholder="3000000" />
        </div>
        <div>
          <label style={lbl}>국비 참여율 상한 (%)</label>
          <input type="number" style={inp()} value={form.max_rate} onChange={e => setForm(f => ({ ...f, max_rate: Number(e.target.value) }))} min={10} max={100} />
        </div>
        <div>
          <label style={lbl}>최대 참여 사업 수</label>
          <input type="number" style={inp()} value={form.max_projects} onChange={e => setForm(f => ({ ...f, max_projects: Number(e.target.value) }))} min={1} max={10} />
        </div>
        <div>
          <label style={lbl}>생년월일</label>
          <input type="date" style={inp()} value={form.birth_date ?? ""} onChange={e => setForm(f => ({ ...f, birth_date: e.target.value || null }))} />
        </div>
        <div>
          <label style={lbl}>국가연구자번호</label>
          <input style={inp()} value={form.researcher_no ?? ""} onChange={e => setForm(f => ({ ...f, researcher_no: e.target.value || null }))} placeholder="8자리 숫자" maxLength={20} />
        </div>
        <div>
          <label style={lbl}>입사일</label>
          <input type="date" style={inp()} value={form.hire_date ?? ""} onChange={e => setForm(f => ({ ...f, hire_date: e.target.value || null }))} />
        </div>
        <div>
          <label style={lbl}>퇴사(예정)일</label>
          <input type="date" style={inp()} value={form.resign_date ?? ""} onChange={e => setForm(f => ({ ...f, resign_date: e.target.value || null }))} />
          <div style={{ fontSize: 11, color: "#e53935", marginTop: 3 }}>입력 시 해당 월 이후 사업 자동 제외</div>
        </div>
      </div>
      <SaveCancel onSave={onSave} onClose={onClose} />
    </Modal>
  );
}
