日期：2026-02-26
主题：daily_report_25_26 管理后台一期（聚合总览+前端独立页）

改动摘要：
1) 后端新增聚合接口
- 文件：backend/projects/daily_report_25_26/api/admin_console.py
- 新接口：GET /api/v1/projects/daily_report_25_26/admin/overview
- 逻辑：
  - 读取项目动作位（can_manage_validation/can_manage_ai_settings/can_publish）；
  - 返回校验总开关状态；
  - 返回 AI 设置摘要（模型、模式、开关、API key 数量与掩码）；
  - 返回看板缓存状态与缓存发布任务快照。

2) 项目路由挂载
- 文件：backend/projects/daily_report_25_26/api/router.py
- 行为：新增 admin_console_router 挂载。

3) 前端新增管理后台页
- 文件：frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 主要模块：
  - 概览卡（授权状态）；
  - 校验总开关控制；
  - AI 设置编辑与保存；
  - 看板缓存发布/刷新/取消/禁用。

4) 前端路由与 API
- 文件：frontend/src/router/index.js
  - 新增 /projects/:projectKey/pages/:pageKey/admin-console
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
  - 新增 getAdminOverview(projectKey)
- 文件：frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue
  - 新增 admin_console 页面描述与导航分支。

5) 配置与权限
- backend_data/shared/项目列表.json
  - 新增 admin_console 页面配置。
- backend_data/shared/auth/permissions.json
  - Global_admin / Group_admin 的 page_access 增加 admin_console。

6) 文档留痕
- configs/progress.md
- backend/README.md
- frontend/README.md

验证说明：
- 本轮未运行自动化构建/测试，仅完成代码链路静态核对与配置一致性核对。