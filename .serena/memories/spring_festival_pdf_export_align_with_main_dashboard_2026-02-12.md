时间：2026-02-12
问题：mini 看板 PDF 导出报 jspdf 模块错误。
处置：将 SpringFestivalDashboardView.vue 的导出链路从模块导入改为主看板同款的 window.html2canvas + window.jspdf.jsPDF；导出版式改为 210mm 宽长页单图导出；保留导出状态与错误提示。并卸载 frontend 本地依赖 html2canvas/jspdf，统一使用 index.html CDN 全局脚本。
涉及文件：frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue，frontend/package.json，frontend/package-lock.json，configs/progress.md，frontend/README.md，backend/README.md。
验证：frontend npm run build 通过。