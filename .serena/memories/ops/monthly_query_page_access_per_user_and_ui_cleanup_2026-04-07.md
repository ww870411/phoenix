时间：2026-04-07
主题：月度查询页访问权限改为逐账号管理，并移除界面中的“用户覆盖”列

变更摘要：
- backend/services/auth_manager.py：新增 list_user_page_access 与 update_user_project_page_access_override；用户级项目覆盖现在同时支持 permissions.json.user_overrides.projects.<project>.actions 与 page_access。
- backend/api/v1/admin_console.py：新增 GET/POST /admin/projects/{project_key}/page-access-users，用于 monthly_data_show/query-tool 的逐账号访问权限管理。
- frontend/src/projects/daily_report_25_26/services/api.js：新增 getAdminProjectPageAccessUsers / setAdminProjectPageAccessUser。
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue：月度查询页访问权限板块改为逐账号表格；日报提交权限板块移除“用户覆盖”列。
- backend_data/shared/auth/permissions.json：将 beifang_admin 的旧格式覆盖整理为 actions.can_submit=false。
- configs/progress.md、frontend/README.md、backend/README.md 已同步。

验证证据：
- python -m py_compile backend/services/auth_manager.py backend/api/v1/admin_console.py 通过。
- frontend 目录 npm run build 通过。

设计说明：
- 界面不再展示“用户覆盖”，但内部仍保留“组默认 + 账号单独设置”的权限模型，只是统一收口到 permissions.json。