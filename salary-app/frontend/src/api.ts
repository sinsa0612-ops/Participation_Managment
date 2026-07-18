// 빈 base = 같은 출처로 호출. 개발은 vite proxy가, 프로덕션은 백엔드가 같은 출처에서 서빙.
const BASE = "";

export type EmployType = "정규직" | "전문직" | "위촉직";
export type Rank = "단장" | "센터장" | "팀장" | "연구원";
export type Role = "연구책임자" | "실무자" | "일반참여자";
export type OrgRole = "주관" | "참여";  // 주관/참여기관 구분(#5) — 주관 사업 책임자만 3책 카운트
export type FundingSource = "정부수탁" | "기본사업";  // 재원 구분(#6) — 국비 100% / 전체 130% 상한

export interface Member {
  id: string;
  name: string;
  employ_type: EmployType;
  rank: Rank;
  salary: number;
  max_rate: number;
  max_projects: number;
  hire_date: string | null;
  resign_date: string | null;
  birth_date: string | null;
  researcher_no: string | null;
}

export interface RequiredMembers {
  chief: string | null;
  staff: string[];
}

export interface MemberConstraint {
  max_rate: number;
}

export interface Project {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  year_budgets: Record<string, number>;
  required_members: RequiredMembers;
  member_constraints: Record<string, MemberConstraint>;
  member_months: Record<string, string[]>;  // { memberId: ["YYYY-MM", ...] }
  sort_order?: number;  // 예산 소진 우선순위 (#2)
  excluded_members?: string[];  // 이 사업에서 배제할 연구원 (#3)
  org_role: OrgRole;  // 주관/참여기관 (#5)
  funding_source: FundingSource;  // 정부수탁/기본사업 (#6)
}

export interface Participation {
  id: string;
  project_id: string;
  member_id: string;
  role: Role;
  start_date: string;
  end_date: string;
  rate: number;
  cost: number;
  member_name?: string;
  employ_type?: EmployType;
  rank?: string;
  proj_name?: string;
  months?: number;
  monthly_cost?: number;  // 월별 인건비(천원 내림) — 백엔드 calc.py가 계산한 SSOT 값
}

export interface MemberStat {
  member_id: string;
  member_name: string;
  employ_type: EmployType;
  rank: Rank;
  proj_count: number;
  max_concurrent: number;
  total_rate: number;
  total_cost: number;
  max_rate: number;
  max_projects: number;
  status: "정상" | "미배분" | "초과";
}

/** 백엔드 오류 응답의 detail(문자열 또는 검증 오류 배열)을 사람이 읽을 메시지로 변환 (F13) */
async function errorMessage(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
      const msgs = data.detail.map((d: { msg?: string }) => d.msg ?? "").filter(Boolean);
      if (msgs.length) return msgs.join(", ");
    }
  } catch {
    /* JSON 파싱 실패 시 상태 코드로 폴백 */
  }
  return `${res.status} ${res.statusText}`;
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(await errorMessage(res));
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Members ──────────────────────────────────────
export const getMembers = () => req<Member[]>("/members/");
export const createMember = (body: Omit<Member, "id">) =>
  req<Member>("/members/", { method: "POST", body: JSON.stringify(body) });
export const updateMember = (id: string, body: Omit<Member, "id">) =>
  req<Member>(`/members/${id}`, { method: "PUT", body: JSON.stringify(body) });
export const deleteMember = (id: string) =>
  req<void>(`/members/${id}`, { method: "DELETE" });

// ── Projects ─────────────────────────────────────
export const getProjects = () => req<Project[]>("/projects/");
export const createProject = (body: Omit<Project, "id">) =>
  req<Project>("/projects/", { method: "POST", body: JSON.stringify(body) });
export const updateProject = (id: string, body: Omit<Project, "id">) =>
  req<Project>(`/projects/${id}`, { method: "PUT", body: JSON.stringify(body) });
export const deleteProject = (id: string) =>
  req<void>(`/projects/${id}`, { method: "DELETE" });
export const reorderProjects = (order: string[]) =>
  req<{ ok: boolean }>("/projects/reorder", { method: "PUT", body: JSON.stringify({ order }) });
export const updateMemberMonths = (projectId: string, memberMonths: Record<string, string[]>) =>
  req<{ member_months: Record<string, string[]> }>(`/projects/${projectId}/member-months`, {
    method: "PUT",
    body: JSON.stringify({ member_months: memberMonths }),
  });
export const updateExclusions = (projectId: string, memberIds: string[]) =>
  req<{ member_ids: string[] }>(`/projects/${projectId}/exclusions`, {
    method: "PUT",
    body: JSON.stringify({ member_ids: memberIds }),
  });

// ── CSV Import ────────────────────────────────────
export interface CsvImportResult {
  created: number;
  errors: string[];
}

async function uploadCsv(path: string, file: File): Promise<CsvImportResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

export const importMembersCSV = (file: File) => uploadCsv("/members/import-csv", file);
export const importProjectsCSV = (file: File) => uploadCsv("/projects/import-csv", file);

// ── Participations ────────────────────────────────
export interface DistributeResult {
  participations: Participation[];
  warnings: string[];  // 강제 참여 실패 등 안내 (#4)
}
export const runDistribute = () =>
  req<DistributeResult>("/participations/distribute", { method: "POST" });
export const getParticipations = () => req<Participation[]>("/participations/");
export const getMemberStats = () => req<MemberStat[]>("/participations/stats");

// ── 예산 미소진 사유 (F17 / Path A) ───────────────
export interface BudgetStatus {
  project_id: string;
  project_name: string;
  budget: number;
  allocated: number;
  remaining: number;
  reason: "ok" | "no_budget" | "saturated" | "slack";
  detail: string;
  recruitable: string[];
}
export const getBudgetStatus = () => req<BudgetStatus[]>("/participations/budget-status");

// ── 수동 조정 (F12) ───────────────────────────────
export interface Override {
  id: string;
  project_id: string;
  member_id: string;
  rate: number;
}
export const getOverrides = () => req<Override[]>("/participations/overrides");
export const setOverride = (project_id: string, member_id: string, rate: number) =>
  req<Override>("/participations/override", { method: "PUT", body: JSON.stringify({ project_id, member_id, rate }) });
export const deleteOverride = (project_id: string, member_id: string) =>
  req<void>(`/participations/override?project_id=${project_id}&member_id=${member_id}`, { method: "DELETE" });
