时间：2026-03-05
用户指令：去掉当前表格模板设计页面。

执行结果：已完成模板设计器页面全链路下线。

前端变更：
1) 删除页面文件
- frontend/src/projects/daily_report_25_26/pages/TemplateDesignerView.vue

2) 删除路由与入口
- frontend/src/router/index.js：删除 template-designer 路由
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue：删除“模板设计器（新表）”标签与 openTemplateDesigner 跳转函数

3) 删除模板设计器 API 调用封装
- frontend/src/projects/daily_report_25_26/services/api.js：删除 list/get/create/update/publishTemplateDesigner* 函数

后端与配置变更：
1) backend/projects/daily_report_25_26/api/router.py
- 删除 template_designer 路由挂载与导入

2) backend/projects/daily_report_25_26/api/template_designer.py
- 删除文件

3) backend/api/v1/routes.py
- 删除项目页面列表中 template_designer 可见性兜底逻辑

4) backend_data/shared/项目列表.json
- 删除 template_designer 页面定义

5) backend_data/shared/auth/permissions.json
- 删除 template_designer 页面键

验证：
- frontend/src 与 backend（代码文件）检索不再存在 template_designer/template-designer/TemplateDesignerView 引用。
- backend_data/shared/项目列表.json 与 auth/permissions.json 中不再存在 template_designer 条目。