日期：2026-02-26
主题：管理后台从项目页改为全局公共页面（仅 Global_admin）

用户要求：
1) 入口改到页头用户信息左侧，文案“进入后台”；
2) 仅 Global_admin 可见与可访问；
3) 后台不归属任何项目模块。

实施结果：
1) 后端
- 新增全局路由模块：backend/api/v1/admin_console.py
- 接口路径统一为 /api/v1/admin/*（overview/validation/ai-settings/cache）
- routes.py 已挂载 admin_console_router
- 移除项目级后台：
  - backend/projects/daily_report_25_26/api/router.py 取消后台挂载
  - 删除 backend/projects/daily_report_25_26/api/admin_console.py

2) 权限模型
- backend/services/auth_manager.py 与 backend/schemas/auth.py 新增动作位：can_access_admin_console
- 权限配置文件 backend_data/shared/auth/permissions.json：
  - 仅 Global_admin 组级 actions 配置 can_access_admin_console=true
  - Group_admin 等未配置该动作位（默认 false）

3) 前端
- AppHeader.vue：用户信息左侧新增“进入后台”按钮，跳转 /admin-console
- router/index.js：新增全局路由 /admin-console（移除项目参数路由）
- AdminConsoleView.vue：改为调用全局 /api/v1/admin/*，并在无权限时跳回 /projects
- store/auth.js：新增 canAccessAdminConsole（读取 permissions.actions.can_access_admin_console）

4) 配置清理
- backend_data/shared/项目列表.json 删除 admin_console 页面项
- backend_data/shared/auth/permissions.json 删除项目 page_access 中的 admin_console

留痕文件：
- configs/progress.md
- backend/README.md
- frontend/README.md