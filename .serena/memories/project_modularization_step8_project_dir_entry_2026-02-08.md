日期：2026-02-08
主题：项目模块化第八步（项目目录入口落地）

新增目录与文件：
- backend/projects/__init__.py
- backend/projects/daily_report_25_26/__init__.py
- backend/projects/daily_report_25_26/api/__init__.py
- backend/projects/daily_report_25_26/api/router.py

关键改动：
- backend/api/v1/project_router_registry.py
  - 路由导入来源改为 `backend.projects.daily_report_25_26.api.router`

设计说明：
- 当前为“入口迁移过渡层”：
  - 项目目录中已存在标准入口；
  - 入口内部暂复用旧实现 `backend.api.v1.daily_report_25_26`，避免一次性大迁移风险。

效果：
- 主路由挂载路径不变，前端无感；
- 代码组织开始向按项目目录聚拢，为后续逐段拆分旧大文件做准备。