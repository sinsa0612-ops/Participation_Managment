import * as XLSX from "xlsx";
import type { Member, Project, Participation } from "../api";
import { toM } from "./format";

/** 선택 연도의 연구원별 월별 참여율·인건비를 엑셀로 내보낸다. */
export function exportMonthlyExcel(
  members: Member[],
  projects: Project[],
  participations: Participation[],
  distYear: number,
) {
  const monthLabels = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"];
  const wb = XLSX.utils.book_new();

  const yrS = distYear * 12 + 1;
  const yrE = distYear * 12 + 12;

  // 참여가 있는 연구원만
  const targetMembers = members.filter((m) =>
    participations.some((r) => r.member_id === m.id && toM(r.end_date) >= yrS && toM(r.start_date) <= yrE),
  );

  // 전체 요약 시트: 연구원 × 월 참여율 합계
  const summaryHeader = ["연구원", "고용형태", "직급", ...monthLabels, "연간합계(%)"];
  const summaryRows = targetMembers.map((m) => {
    const myParts = participations.filter(
      (r) => r.member_id === m.id && toM(r.end_date) >= yrS && toM(r.start_date) <= yrE,
    );
    const monthRates = Array.from({ length: 12 }, (_, i) => {
      const mi = yrS + i;
      return myParts.filter((r) => toM(r.start_date) <= mi && mi <= toM(r.end_date)).reduce((s, r) => s + r.rate, 0);
    });
    const annualSum = monthRates.reduce((s, r) => s + r, 0);
    return [m.name, m.employ_type, m.rank, ...monthRates.map((r) => (r > 0 ? r : "")), annualSum > 0 ? annualSum : ""];
  });
  const summarySheet = XLSX.utils.aoa_to_sheet([summaryHeader, ...summaryRows]);
  summarySheet["!cols"] = [{ wch: 10 }, { wch: 8 }, { wch: 8 }, ...Array(13).fill({ wch: 7 })];
  XLSX.utils.book_append_sheet(wb, summarySheet, `${distYear}년_참여율요약`);

  // 연구원별 시트
  for (const m of targetMembers) {
    const myParts = participations.filter(
      (r) => r.member_id === m.id && toM(r.end_date) >= yrS && toM(r.start_date) <= yrE,
    );
    const activeProjs = projects.filter((p) => myParts.some((r) => r.project_id === p.id));
    const monthNums = Array.from({ length: 12 }, (_, i) => yrS + i);

    const rows: (string | number)[][] = [];
    rows.push([`연구원: ${m.name}`, `고용형태: ${m.employ_type}`, `직급: ${m.rank}`, `월인건비: ${m.salary.toLocaleString("ko-KR")}원`]);
    rows.push([]);

    // 참여율(%) 표
    rows.push(["[참여율 %]", "", ...monthLabels]);
    for (const p of activeProjs) {
      const part = myParts.find((r) => r.project_id === p.id);
      if (!part) continue;
      const rateRow: (string | number)[] = [p.name, ""];
      for (const mi of monthNums) {
        rateRow.push(toM(part.start_date) <= mi && mi <= toM(part.end_date) ? part.rate : "");
      }
      rows.push(rateRow);
    }
    const totalRateRow: (string | number)[] = ["합계", ""];
    for (const mi of monthNums) {
      const total = myParts.filter((r) => toM(r.start_date) <= mi && mi <= toM(r.end_date)).reduce((s, r) => s + r.rate, 0);
      totalRateRow.push(total > 0 ? total : "");
    }
    rows.push(totalRateRow);
    rows.push([]);

    // 인건비(원) 표
    rows.push(["[인건비 원]", "", ...monthLabels]);
    for (const p of activeProjs) {
      const part = myParts.find((r) => r.project_id === p.id);
      if (!part) continue;
      const costRow: (string | number)[] = [p.name, ""];
      const monthlyCost = part.monthly_cost ?? 0; // SSOT: 백엔드 calc.py 값
      for (const mi of monthNums) {
        costRow.push(toM(part.start_date) <= mi && mi <= toM(part.end_date) ? monthlyCost : "");
      }
      rows.push(costRow);
    }
    const totalCostRow: (string | number)[] = ["합계", ""];
    for (const mi of monthNums) {
      const total = myParts
        .filter((r) => toM(r.start_date) <= mi && mi <= toM(r.end_date))
        .reduce((s, r) => s + (r.monthly_cost ?? 0), 0);
      totalCostRow.push(total > 0 ? total : "");
    }
    rows.push(totalCostRow);

    const ws = XLSX.utils.aoa_to_sheet(rows);
    ws["!cols"] = [{ wch: 20 }, { wch: 4 }, ...Array(12).fill({ wch: 9 })];
    const sheetName = m.name.slice(0, 28); // 시트 이름 30자 제한
    XLSX.utils.book_append_sheet(wb, ws, sheetName);
  }

  XLSX.writeFile(wb, `월별참여율_${distYear}년.xlsx`);
}
