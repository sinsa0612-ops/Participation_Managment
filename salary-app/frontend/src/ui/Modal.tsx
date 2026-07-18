import type { CSSProperties, ReactNode } from "react";
import { btn } from "./styles";

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
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

export function SaveCancel({ onSave, onClose }: { onSave: () => void; onClose: () => void }) {
  return (
    <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
      <button onClick={onSave} style={btn("#4f6ef7", "#fff", { flex: 1, padding: "10px" } as CSSProperties)}>저장</button>
      <button onClick={onClose} style={btn("#f5f5f5", "#555", { flex: 1, padding: "10px" } as CSSProperties)}>취소</button>
    </div>
  );
}
