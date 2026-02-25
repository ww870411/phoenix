日期：2026-02-25
主题：权限文件模块化实施（项目>页面）

实施摘要：
1) 后端权限核心改造
- 文件：backend/services/auth_manager.py
- 新增：ProjectPermissions 数据结构。
- 扩展：GroupPermissions.projects、AuthSession.allowed_units_by_project。
- 新增会话方法：
  - resolve_project_permissions(project_key)
  - get_project_page_access(project_key)
  - get_project_action_flags(project_key)
  - resolve_allowed_units(project_key)
- _load_permissions 支持解析 groups.*.projects.* 并兼容旧字段回退。

2) 后端接口生效点改造
- backend/api/v1/routes.py::list_project_pages 按 project_id 使用项目页面权限过滤。
- backend/projects/daily_report_25_26/api/dashboard.py 使用项目维度 can_publish。
- backend/projects/daily_report_25_26/api/legacy_full.py 审批/撤销/发布与单位过滤切换为项目维度读取。

3) 后端 schema 扩展
- 文件：backend/schemas/auth.py
- PermissionsModel 增加 projects 字段（ProjectPermissionsModel）。

4) 前端权限消费改造
- 文件：frontend/src/projects/daily_report_25_26/store/auth.js
- 新增 resolveProjectPermission(projectKey)；
- filterPages/filterSheetsByRule 支持 projectKey（兼容旧签名）；
- 新增 canSubmitFor/canApproveFor/canRevokeFor/canPublishFor；
- canApproveUnit/canRevokeUnit 增加项目维度单位判断。
- 调用点更新：PageSelectView.vue、Sheets.vue。

5) 配置迁移
- 文件：backend_data/shared/auth/permissions.json
- 已新增 groups.*.projects 分层。
- daily_report_25_26 权限已按项目归档。
- Global_admin 增加 daily_report_spring_festval_2026 -> mini_entry 项目权限。

兼容策略：
- 代码层保留旧平铺字段回退能力；
- 新结构优先，旧结构可作为应急回滚路径。

本次同步文档：
- configs/progress.md
- backend/README.md
- frontend/README.md