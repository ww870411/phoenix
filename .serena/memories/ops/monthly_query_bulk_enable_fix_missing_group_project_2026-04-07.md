时间：2026-04-07
主题：修复月度查询页逐账号“全部允许”后仍显示禁止访问的问题

问题根因：
- 某些账号所属分组在 groups.projects 中本来没有 monthly_data_show 项目条目。
- 用户级 page_access 覆盖虽然写入了 permissions.json.user_overrides，但 _apply_user_project_overrides 在 base_project 为 None 时直接跳过，导致覆盖不生效。

修复内容：
- backend/services/auth_manager.py：在 _apply_user_project_overrides 中，当用户级覆盖命中但组级缺少该项目时，补建临时 ProjectPermissions（空 page_access、空 sheet_rules、继承组 units_access 与 actions），再应用账号级 actions/page_access 覆盖。
- configs/progress.md、frontend/README.md、backend/README.md 已同步补充修复记录。

验证证据：
- python -m py_compile backend/services/auth_manager.py backend/api/v1/admin_console.py 通过。
- frontend 目录 npm run build 通过。