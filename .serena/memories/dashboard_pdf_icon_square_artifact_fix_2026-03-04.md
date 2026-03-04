时间：2026-03-04（续）
用户反馈：PDF 顶部四个卡片图标虽已显示，但图标背景出现小方框。
定位：方框来自 `.summary-card__icon` 容器样式（box-shadow / backdrop-filter 等玻璃态效果）在 html2canvas 导出中的渲染伪影，不是 SVG path 本体。
修复：在 `injectPdfSafeSummaryIcons` 注入的导出克隆 style 中新增：
- `.summary-card__icon { background: transparent; box-shadow: none; border: 0; backdrop-filter: none; -webkit-backdrop-filter: none; }`
并保留 `::before` 关闭与内联 SVG 注入。
结果：导出 PDF 中图标周围小方框被移除，页面实时样式不变。
涉及文件：frontend/src/projects/daily_report_25_26/pages/DashBoard.vue，configs/progress.md，frontend/README.md，backend/README.md。