时间：2026-02-11
任务：将春节项目页面从 daily_report_25_26 目录迁移到独立项目目录。

变更摘要：
1) 路由迁移
- frontend/src/router/index.js
  - /projects/:projectKey 组件路径改为 ../projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue

2) 新增独立项目目录文件
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalEntryView.vue
- frontend/src/projects/daily_report_spring_festval_2026/services/api.js

3) 删除旧文件
- frontend/src/daily_report_25_26/pages/SpringFestivalEntryView.vue

4) 兼容与复用策略
- 新项目 services/api.js 复用 shared 请求函数（daily_report_25_26/services/api.js 中 extractSpringFestivalJson），保持鉴权与请求行为一致。
- ProjectSelectView 的直达入口保持不变：daily_report_spring_festval_2026 直达 /projects/{projectKey}。

5) 文档留痕
- frontend/README.md 更新新路径。
- backend/README.md 补充“前端目录规范化协同状态”。
- configs/progress.md 记录本次迁移。

结果：春节项目前端目录边界已独立，满足“新项目规范化”诉求。