时间：2026-03-04
需求：用户确认模板设计器入口应放在管理后台，而非页面选择区。

实现：
1) frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 顶部新增“模板设计器（新表）”按钮
- 新增 openTemplateDesigner()，跳转到 /projects/daily_report_25_26/pages/template_designer/template-designer

2) frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue
- 移除 template_designer 专用跳转分支
- 新增 HIDDEN_PAGE_KEYS 过滤，在页面选择页隐藏 template_designer 卡片

3) 文档留痕
- configs/progress.md
- frontend/README.md
- backend/README.md

结果：模板设计器入口统一收敛到管理后台，避免用户在页面选择区误找。