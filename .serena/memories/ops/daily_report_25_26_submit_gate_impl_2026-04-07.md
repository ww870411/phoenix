时间：2026-04-07
主题：daily_report_25_26 默认关闭普通用户提交并接入 admin-console 用户级提交开关

实施结果：
1. 默认策略调整
- 文件：backend_data/shared/auth/permissions.json
- 处理：保留 Global_admin 的 daily_report_25_26.can_submit=true；将 Group_admin、ZhuChengQu_admin、Unit_admin、unit_filler、shoudian_filler 等非 Global_admin 相关组在 daily_report_25_26 下的 can_submit 调整为 false。
- 结果：日报项目默认关闭普通账号提报。

2. 账户文件支持用户级项目动作覆盖
- 文件：backend/services/auth_manager.py
- UserRecord 新增 project_action_overrides。
- _load_accounts 解析 账户信息.json 中可选 project_actions。
- 新增 _merge_action_flags / _apply_user_project_overrides / _build_session。
- login 与 _load_persistent_session 均改为构造“组权限 + 用户覆盖”后的会话。
- _ensure_loaded 由“配置变更时清空所有会话”改为“刷新在线会话权限”。
- 新增 list_daily_submit_users / update_user_project_action_override，供后台管理接口复用。

3. 后端提交接口补强校验
- 文件：backend/projects/daily_report_25_26/api/legacy_full.py
- submit_debug 新增 Depends(get_current_session) 与 can_submit 校验。
- 结果：即使绕过前端直接调用提交接口，也会被 403 拦截。

4. 管理后台新增用户级提交权限模块
- 文件：backend/api/v1/admin_console.py
- 新增接口：
  - GET /admin/projects/{project_key}/submit-permissions
  - POST /admin/projects/{project_key}/submit-permissions
- 当前仅支持 daily_report_25_26 和 can_submit。
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
- 新增 getAdminProjectSubmitPermissions / setAdminProjectSubmitPermission。
- 文件：frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 新增“日报提交权限”板块，展示非 Global_admin 用户并支持逐个开启/关闭。

5. 前端提交页联动
- 文件：frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue
- 新增 canSubmitCurrentProject 计算属性。
- 提交按钮在无权限时禁用并显示“当前账号无提交权限”。
- onSubmit 首段新增权限提示并阻断。

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md

验证说明：
- 使用 Serena 符号概览确认 backend/services/auth_manager.py 与 backend/api/v1/admin_console.py 语法结构可被正常解析。
- 未执行前端构建与端到端联调。