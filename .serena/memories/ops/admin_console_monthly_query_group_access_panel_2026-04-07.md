时间：2026-04-07
主题：在 admin-console 增加 monthly_data_show/query-tool 的用户组访问权限面板

变更摘要：
- backend/services/auth_manager.py：新增 list_group_page_access 与 update_group_page_access，直接读写 backend_data/shared/auth/permissions.json 中各用户组的 projects.monthly_data_show.page_access。
- backend/api/v1/admin_console.py：新增 GET/POST /admin/projects/{project_key}/page-access-groups，当前仅允许 monthly_data_show + projects_monthly_data_show_query_tool。
- frontend/src/projects/daily_report_25_26/services/api.js：新增 getAdminProjectPageAccessGroups / setAdminProjectPageAccessGroup。
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue：新增“月度查询页访问权限”板块，默认折叠，支持单组切换与全部开启/关闭，不展示 Global_admin。
- configs/progress.md、frontend/README.md、backend/README.md 已同步追加记录。

验证证据：
- python -m py_compile backend/services/auth_manager.py backend/api/v1/admin_console.py 通过。
- frontend 目录 npm run build 通过。

设计说明：
- 未新增权限配置文件，继续沿用 permissions.json 作为唯一用户组页面访问来源。
- 面板仅控制组级 page_access，不影响 Global_admin，也不改账户级 project_actions。