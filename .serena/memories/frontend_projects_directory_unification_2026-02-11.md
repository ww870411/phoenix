时间：2026-02-11
任务：将 daily_report_25_26 迁移到 frontend/src/projects 下并统一引用。

关键变更：
1) 目录迁移
- 原路径：frontend/src/daily_report_25_26
- 新路径：frontend/src/projects/daily_report_25_26
- 迁移后 frontend/src 顶层项目仅通过 projects/* 管理。

2) 路径修正
- main.js: 主题样式改为 ./projects/daily_report_25_26/styles/theme.css
- router/index.js: auth store 与各业务页面组件导入改为 ../projects/daily_report_25_26/...
- pages/LoginView.vue、pages/ProjectSelectView.vue: 导入改为 ../projects/daily_report_25_26/...
- 春节项目复用路径改为相对 projects 目录：
  - projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue
  - projects/daily_report_spring_festval_2026/services/api.js

3) 文档同步
- frontend/README.md：补充“项目目录已统一到 frontend/src/projects/”
- backend/README.md：补充协同状态，说明 daily_report_25_26 前端模块已迁移
- configs/progress.md：新增本次迁移记录
- frontend/src/projects/daily_report_25_26/README.md：修正 main.js 样式路径示例

结果：项目目录组织已规范为“全局壳层 pages + 项目目录 projects/*”模式，满足多项目并列维护诉求。