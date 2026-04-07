时间：2026-04-07
主题：daily_report_25_26 停止常规用户填报并在 admin-console 增加用户级提交开关的设计评估

现状结论：
1. 现有权限模型已支持项目级动作权限：backend_data/shared/auth/permissions.json -> groups.*.projects.daily_report_25_26.actions.can_submit。
2. 前端权限消费已提供 useAuthStore.canSubmitFor(projectKey)，位置：frontend/src/projects/daily_report_25_26/store/auth.js。
3. 但 DataEntryView 当前未使用 canSubmitFor 控制提交按钮，实际仅按日期只读限制 submitDisabled；提交按钮未接项目权限。
4. 后端提交接口 backend/projects/daily_report_25_26/api/legacy_full.py::submit_debug 当前没有 Depends(get_current_session)，也没有 can_submit 校验，属于执行层未真正落地权限控制。
5. admin-console 当前项目设定页仅接入：设定概览、数据校验总开关、AI 设置、看板功能设置；未接入账号/用户权限管理。
6. 账户信息为按组存储：backend_data/shared/auth/账户信息.json；ww870411 是 Global_admin 组下账号。

设计建议：
1. 不直接把“按用户可提交”塞进 permissions.json，因为该文件当前是按组模型。
2. 新增一层用户级覆盖配置，建议路径：backend_data/shared/auth/user_permission_overrides.json。
3. 推荐结构：users.<username>.projects.daily_report_25_26.actions.can_submit = true/false。
4. AuthManager 登录/会话构建阶段合并：组权限为基线，用户覆盖仅覆盖指定项目动作位。
5. 管理后台新增一个“日报提报权限”板块，仅在 selectedProjectKey == daily_report_25_26 时显示；列出非 Global_admin 账号并允许切换 can_submit。
6. 后端新增 admin-console 用户提交权限查询/更新接口；前端在 AdminConsoleView 调用该接口。
7. 提交链路必须双重生效：
   - 前端 DataEntryView 使用 auth.canSubmitFor(projectKey) 禁用提交按钮并提示。
   - 后端 submit_debug 增加会话依赖与 can_submit 校验，避免绕过前端直接提交。

范围判断：
- 这项改动会影响 daily_report_25_26 提交入口与 admin-console 项目设定页，不应影响 dashboard/data_show/query。
- user override 方案可保留后续扩展空间，用于其他项目或其他动作位。