日期：2026-02-25
主题：项目入口可见性/可访问性是否可由 backend_data/shared/项目列表.json 配置

结论：
1) 是否显示项目：可通过是否存在项目条目实现（删除或保留条目）。
2) 哪些用户能看到项目：当前不支持由项目列表文件配置。`backend/api/v1/routes.py::list_projects` 不做按用户过滤。
3) 哪些用户可点击访问项目：当前无通用项目级配置能力。权限模型为页面级（page_access/sheet_rules/units_access/actions），见 backend/schemas/auth.py 与 backend/services/auth_manager.py。
4) 前端存在特例硬编码：frontend/src/pages/ProjectSelectView.vue 对 daily_report_spring_festval_2026 在点击时限制仅 Global_admin。

本次改动文件：
- configs/progress.md
- backend/README.md
- frontend/README.md

备注：本轮无业务代码改造，仅能力核对与留痕。