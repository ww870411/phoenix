日期：2026-02-25
主题：三类硬编码权限统一迁移到 permissions.json

范围：
1) 项目入口可见性/可访问性
2) 后端角色白名单判断
3) 前端角色名显隐判断

核心实现：
- ActionFlags 扩展新动作位：
  - can_manage_modularization
  - can_manage_validation
  - can_manage_ai_settings
  - can_manage_ai_sheet_switch
  - can_extract_xlsx
  - can_unlimited_ai_usage

后端改造：
- backend/services/auth_manager.py
  - 解析/返回新动作位；新增 has_project_access(project_key)。
- backend/schemas/auth.py
  - ActionFlagsModel 增加新字段。
- backend/api/v1/routes.py
  - GET /projects 改为鉴权后按项目权限过滤。
  - modularization 接口改为 can_manage_modularization。
- backend/projects/daily_report_25_26/api/legacy_full.py
  - validation 开关 -> can_manage_validation
  - AI settings -> can_manage_ai_settings
  - sheet ai-switch -> can_manage_ai_sheet_switch
- backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py
  - extract 权限 -> can_extract_xlsx
- backend/services/ai_usage_service.py
  - unlimited 判定改为 can_unlimited_ai_usage（移除组名白名单）

前端改造：
- frontend/src/pages/ProjectSelectView.vue
  - 删除 spring 项目 Global_admin 硬编码拦截。
- frontend/src/projects/daily_report_25_26/store/auth.js
  - 新增 canManageValidationFor/canManageAiSettingsFor/canExtractXlsxFor。
- frontend/src/projects/daily_report_25_26/pages/Sheets.vue
  - 使用 canManageValidationFor(projectKey)。
- frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue
  - 使用 canManageValidationFor(projectKey)。
- frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue
  - 使用 canManageAiSettingsFor(projectKey)。
- frontend/src/projects/daily_report_25_26/components/UnitAnalysisLite.vue
  - 使用 canManageAiSettingsFor(props.projectKey)。

配置：
- backend_data/shared/auth/permissions.json 补齐对应动作位。

备注：
- 本轮未运行自动化测试，已完成代码链路与引用点核对。