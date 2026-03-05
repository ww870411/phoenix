时间：2026-03-05
需求：用户要求将管理后台中的“模板设计器（新表）”从独立按钮改为与其他子页面并列标签。

接入校验：
- 已执行 serena__activate_project（phoenix）与 serena__check_onboarding_performed（已完成）。

实现：
1) frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 在顶部 tab-group 内新增并列标签按钮：模板设计器（新表）
- 移除顶部右侧 top-actions 独立按钮
- 保留 openTemplateDesigner 既有跳转逻辑，确保路由链路不变
- 删除未使用样式 .top-actions

2) 文档同步（按仓库规范）
- configs/progress.md：新增“2026-03-05（模板设计器入口改为管理后台并列标签）”
- frontend/README.md：新增“结构同步（2026-03-05 模板设计器入口并列标签化）”
- backend/README.md：新增“结构同步（2026-03-05 模板设计器入口并列标签化前端联动）”

结果：
- 模板设计器入口形态与管理后台其他子页面统一为并列标签，不再是独立按钮。
- 后端接口、权限和模板设计器页面功能无改动。