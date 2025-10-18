时间：2025-10-19
变更文件：
- frontend/src/daily_report_25_26/pages/Sheets.vue（新增，承载原 DashboardView 逻辑）
- frontend/src/router/index.js（懒加载路径改为 Sheets.vue）
- frontend/README.md、backend/README.md（同步命名说明）
- configs/progress.md（留痕记录）

背景：前端路由固定为 /projects/:projectKey/sheets，需要组件命名与之对应。

处理：将 DashboardView.vue 改名为 Sheets.vue，并在 README/进度日志中更新引用路径，避免命名与路由不一致导致的困惑。

验证建议：
- npm run dev 启动前端后，访问 /projects → 选择项目，应加载 /projects/:projectKey/sheets 并正确渲染页面。
- 检查浏览器调试面板，确保异步加载的组件路径为 pages/Sheets.vue。

回滚思路：若需恢复旧命名，重新创建 DashboardView.vue 并调整 router 与文档即可。