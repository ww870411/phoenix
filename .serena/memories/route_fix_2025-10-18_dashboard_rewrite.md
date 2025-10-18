时间：2025-10-18
变更文件：
- frontend/src/daily_report_25_26/pages/DashboardView.vue（完整重写 template/script/style）
- configs/progress.md（记录修复编译错误与导航）

问题与原因：
- 在 /projects 点击项目名跳转到 /projects/:projectKey/sheets 时，Vite 对 DashboardView.vue 动态编译报错：Invalid end tag，返回 500，导致模块导入失败与页面无响应。

处理方案：
- 用严格闭合、简化且可读的模板重写 DashboardView.vue，保留原有逻辑（获取清单、按单位分组、计算填报状态、跳转至 data-entry）。
- 链接使用命名路由 { name: 'data-entry', params: { projectKey, sheetKey } }，确保与 router 定义一致。

回滚思路：
- 若需回滚，恢复文件至变更前版本。

验证建议：
- 打开 /projects，点击 daily_report_25_26，应成功加载 /projects/daily_report_25_26/sheets；不再出现 “Invalid end tag” 与 500。
- 在看板中点击任一表名，应跳转至 /projects/daily_report_25_26/sheets/<sheet_key> 填报页。