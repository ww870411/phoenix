时间：2026-03-04
问题：daily_report_25_26 数据看板顶部四个摘要卡片图标（当日平均气温、边际利润、原煤消耗、净投诉量）在页面可见，但 PDF 导出后空白。
根因：前端图标渲染方式为 CSS 伪元素 + mask-image(data:svg)，导出链路使用 html2canvas + jsPDF，html2canvas 对该渲染兼容不足导致图形丢失。
实施：
1) frontend/src/projects/daily_report_25_26/pages/DashBoard.vue 新增 SUMMARY_CARD_ICON_PATHS、createSummaryIconSvgElement、injectPdfSafeSummaryIcons。
2) 在 downloadPDF 的 onclone 回调中调用 injectPdfSafeSummaryIcons(clonedDocument)。
3) 在克隆文档中注入导出专用 style：禁用 .summary-card__icon::before，并使用内联 SVG（currentColor）替代，保证截图稳定。
4) 保留既有按钮隐藏与折叠展开导出逻辑，不改页面实时样式。
文档留痕：
- configs/progress.md 新增 2026-03-04 记录。
- frontend/README.md 新增“数据看板 PDF 图标导出修复（2026-03-04）”。
- backend/README.md 新增联动说明（后端无改动）。
结果：导出 PDF 时顶部四个卡片图标可显示，不再空白。