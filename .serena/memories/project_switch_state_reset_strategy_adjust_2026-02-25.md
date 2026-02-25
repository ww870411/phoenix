时间：2026-02-25
主题：切号项目列表修复策略调整（解除 auth 对 useProjects 耦合）

背景：
- 用户反馈数据分析页白屏，需要降低前端状态修复的副作用风险。

变更文件：
1) frontend/src/projects/daily_report_25_26/store/auth.js
2) frontend/src/pages/ProjectSelectView.vue
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

调整内容：
- 移除 auth.js 中 resetProjectsState 的 import 与调用。
- 在 ProjectSelectView onMounted 时执行 resetProjectsState() + ensureProjectsLoaded(true)。

验证：
- frontend 执行 npm run build 通过。

结果：
- 仍可在切号后立即按当前账号刷新项目列表；
- 降低 auth store 级耦合对其他页面初始化链路的影响。