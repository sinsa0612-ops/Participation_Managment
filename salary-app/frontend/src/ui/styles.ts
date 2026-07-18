import type { CSSProperties } from "react";

/* ── 상수 ── */
export const EMPLOYMENT_TYPES = ["정규직", "전문직", "위촉직"] as const;
export const RANKS = ["단장", "센터장", "팀장", "연구원"] as const;

/* ── 테이블 셀 스타일 ── */
export const thS: CSSProperties = {
  padding: "6px 8px", textAlign: "center", color: "#555", fontWeight: 600,
  borderBottom: "1px solid #e0e0e0", borderRight: "1px solid #eeeeee",
  whiteSpace: "nowrap", fontSize: 11, background: "#f7f8fa",
};
export const tdS: CSSProperties = {
  padding: "6px 8px", borderBottom: "1px solid #f5f5f5", borderRight: "1px solid #eeeeee",
  whiteSpace: "nowrap", fontSize: 12, textAlign: "right",
};

/* ── 폼/버튼 스타일 헬퍼 ── */
export const lbl: CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, color: "#555", marginBottom: 4 };

export const inp = (extra: CSSProperties = {}): CSSProperties => ({
  width: "100%", boxSizing: "border-box", border: "1px solid #e0e0e0",
  borderRadius: 7, padding: "7px 10px", fontSize: 13, outline: "none", background: "#fafbfc", ...extra,
});

export const tag = (bg: string, color: string): CSSProperties => ({
  fontSize: 11, background: bg, color, borderRadius: 4, padding: "2px 7px", fontWeight: 600,
});

export const btn = (bg: string, color: string, extra: CSSProperties = {}): CSSProperties => ({
  background: bg, color, border: "none", borderRadius: 7, padding: "6px 13px",
  fontSize: 12, fontWeight: 600, cursor: "pointer", ...extra,
});

export const ROLE_COLOR: Record<string, string> = { 연구책임자: "#4f6ef7", 실무자: "#26a69a", 일반참여자: "#90a4ae" };
export const EMP_COLOR: Record<string, string> = { 정규직: "#5c6bc0", 전문직: "#00897b", 위촉직: "#f4511e" };
