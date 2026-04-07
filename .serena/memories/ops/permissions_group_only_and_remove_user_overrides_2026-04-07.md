时间：2026-04-07
主题：权限模型回归纯分组配置，移除 user_overrides

变更摘要：
- backend/services/auth_manager.py：取消从 permissions.json 加载 user_overrides；_ensure_loaded 仅加载 groups 与 biz_date_offset_days；_apply_user_project_overrides 退化为空操作。新增 list_project_submit_groups 与 update_group_project_action，用于按用户组管理 daily_report_25_26 的 can_submit。
- backend/api/v1/admin_console.py：/admin/projects/{project_key}/submit-permissions 改为返回 groups 并按 group_name 更新；移除月报 query-tool 的逐账号接口 /page-access-users，保留并继续使用 /page-access-groups。
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue：日报提交权限与月度查询页访问权限两个板块都改为按用户组展示；表格字段统一为用户组、层级、账号数、账号列表、当前状态、操作；批量按钮作用于用户组。
- frontend/src/projects/daily_report_25_26/services/api.js：提交权限接口 payload 改为 group_name；删除逐账号月报 query-tool API，仅使用 group 接口。
- backend_data/shared/auth/permissions.json：删除顶层 user_overrides；将此前 monthly_data_show/query-tool 的逐账号例外提升为以下分组的组权限：Group_admin、ZhuChengQu_admin、Unit_admin、unit_filler、shoudian_filler、Group_viewer。
- configs/progress.md、frontend/README.md、backend/README.md 已同步记录当前模型与迁移结果。

验证证据：
- python -m py_compile backend/services/auth_manager.py backend/api/v1/admin_console.py 通过。
- python -c 解析 backend_data/shared/auth/permissions.json 成功，顶层仅剩 metadata 与 groups。
- frontend 目录 npm run build 通过。

说明：
- 这次调整意味着日报提交与月报 query-tool 访问不再支持单账号例外，后续所有权限调整应直接修改分组权限。