时间：2026-03-01
主题：monthly_data_show 页面 BUG 预排查（待用户提供复现步骤）

前置校验：
- serena__activate_project: 已激活 D:\编程项目\phoenix
- serena__check_onboarding_performed: 已完成

排查文件清单：
- 前端：
  - frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
  - frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
  - frontend/src/router/index.js
  - frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue
  - frontend/src/projects/daily_report_25_26/services/api.js
- 后端：
  - backend/projects/monthly_data_show/api/workspace.py
- 配置：
  - backend_data/shared/项目列表.json
  - backend_data/shared/auth/permissions.json

结论：
- /projects/monthly_data_show/pages -> 子页 -> /import-workspace 与 /query-tool 的路由链路存在且已在配置中注册。
- 查询页与后端 query/query-comparison 接口调用参数对齐。
- 当前缺少明确 BUG 现象（报错文本、复现步骤、期望与实际差异），无法安全落地定向修复。

本轮变更：
- configs/progress.md：追加本轮排查记录。
- backend/README.md：追加“本轮无结构改动，仅排查”记录。
- frontend/README.md：追加“本轮无结构改动，仅排查”记录。

降级说明：
- 无 Serena 编辑受阻；未使用 shell 编辑；无降级。