/* 표시용 포맷/날짜 헬퍼 (순수 함수) */

export const getYears = (start: string, end: string): number[] => {
  if (!start || !end) return [];
  const sy = new Date(start).getFullYear(),
    ey = new Date(end).getFullYear();
  return Array.from({ length: ey - sy + 1 }, (_, i) => sy + i);
};

export const genProjMonths = (startDate: string, endDate: string): string[] => {
  if (!startDate || !endDate) return [];
  const months: string[] = [];
  let [sy, sm] = startDate.slice(0, 7).split("-").map(Number);
  const [ey, em] = endDate.slice(0, 7).split("-").map(Number);
  while (sy < ey || (sy === ey && sm <= em)) {
    months.push(`${sy}-${String(sm).padStart(2, "0")}`);
    sm++;
    if (sm > 12) {
      sm = 1;
      sy++;
    }
  }
  return months;
};

export const fmt = (n?: number | null): string => (n == null ? "-" : Math.round(n).toLocaleString("ko-KR"));

/** "YYYY-MM-DD" → 연*12+월 (월 단위 비교용) */
export const toM = (d: string): number => {
  const [y, m] = d.split("-").map(Number);
  return y * 12 + m;
};
