时间：2026-02-12
范围：frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue，frontend/package.json，frontend/package-lock.json，configs/progress.md，frontend/README.md，backend/README.md
变更摘要：
1) 将 mini 看板下载 PDF 从 window.print 改为 html2canvas + jsPDF 直出下载，支持 A4 分页与业务日期命名。
2) 新增 downloadingPdf 状态与按钮禁用文案“正在生成PDF…”。
3) formatIncrement 对 -0 归一化并使用 >=0 正号规则，差异为0显示 +0。
4) 安装依赖 html2canvas 与 jspdf，并完成构建验证。
验证：frontend 执行 npm run build 通过。