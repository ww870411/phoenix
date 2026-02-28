时间：2026-02-28
主题：新增 monthly_data_pull 项目模块（第一阶段骨架）

用户要求：
- 新增项目名 monthly_data_pull，位于项目列表最后。
- 仅 Global_admin 可访问。
- 构建对应前后端项目目录并放置程序文件。
- 默认目录落在 backend_data/monthly_data_pull。

已完成变更：
1) 项目列表与权限
- backend_data/shared/项目列表.json：新增 monthly_data_pull（availability=[Global_admin]，pages.workspace）
- backend_data/shared/auth/permissions.json：Global_admin 新增 monthly_data_pull 项目权限

2) 后端项目骨架
- backend/projects/monthly_data_pull/__init__.py
- backend/projects/monthly_data_pull/api/__init__.py
- backend/projects/monthly_data_pull/api/router.py
- backend/projects/monthly_data_pull/api/workspace.py
- backend/api/v1/project_router_registry.py：注册 monthly_data_pull

3) 后端接口
- GET /api/v1/projects/monthly_data_pull/monthly-data-pull/ping
- GET /api/v1/projects/monthly_data_pull/monthly-data-pull/workspace
  - 返回并确保创建默认目录：mapping_rules/source_reports/target_templates/outputs

4) 数据目录初始化
- backend_data/monthly_data_pull/README.md
- backend_data/monthly_data_pull/workspace_settings.json
- backend_data/monthly_data_pull/mapping_rules/.gitkeep
- backend_data/monthly_data_pull/source_reports/.gitkeep
- backend_data/monthly_data_pull/target_templates/.gitkeep
- backend_data/monthly_data_pull/outputs/.gitkeep

5) 前端入口骨架
- frontend/src/pages/ProjectEntryView.vue（按 projectKey 分发直达入口）
- frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue（项目首页骨架）
- frontend/src/router/index.js：/projects/:projectKey -> ProjectEntryView
- frontend/src/pages/ProjectSelectView.vue：monthly_data_pull 加入直达入口集合
- frontend/src/projects/daily_report_25_26/services/api.js：新增 getMonthlyDataPullWorkspace

6) 文档留痕
- configs/progress.md 新增本次记录
- backend/README.md、frontend/README.md 更新最新结构状态

回滚方式：
- 删除上述新增文件，并回退 7 个修改文件到本次改动前版本即可。