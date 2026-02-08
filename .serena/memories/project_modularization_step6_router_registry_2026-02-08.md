日期：2026-02-08
主题：项目模块化第六步（项目路由注册表）

新增文件：
- backend/api/v1/project_router_registry.py
  - PROJECT_ROUTER_REGISTRY：维护 project_key -> {router, public_router}

改动文件：
- backend/api/v1/routes.py
  - 删除对 `daily_report_25_26` 的硬编码 include。
  - 改为遍历 `PROJECT_ROUTER_REGISTRY` 自动挂载 `/api/v1/projects/<project_key>`。

效果：
- 新增项目路由时，只需在注册表补一项，主路由保持稳定。
- 现有 `daily_report_25_26` 路径保持不变，前端无感。