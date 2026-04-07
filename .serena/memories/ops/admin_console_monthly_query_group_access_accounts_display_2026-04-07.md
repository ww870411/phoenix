时间：2026-04-07
主题：月度查询页用户组访问权限面板补充账号列表展示

变更摘要：
- backend/services/auth_manager.py：`list_group_page_access` 由仅返回 user_count，扩展为同时返回 usernames 列表。
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue：月度查询页访问权限表格新增“账号列表”列，按 `、` 连接显示组内用户名；控制粒度仍为用户组。
- configs/progress.md、frontend/README.md、backend/README.md 已同步补充说明。

验证证据：
- python -m py_compile backend/services/auth_manager.py 通过。
- frontend 目录 npm run build 通过。