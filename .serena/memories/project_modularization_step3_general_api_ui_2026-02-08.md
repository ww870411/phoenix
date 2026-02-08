日期：2026-02-08
主题：项目模块化第三步（通用后端接口 + 前端管理页）

变更摘要：
1) 后端 `backend/api/v1/routes.py`
- 新增系统管理员校验 `_ensure_system_admin`（允许 group: 系统管理员 / Global_admin）。
- 新增文件清单策略：`DEFAULT_PROJECT_CONFIG_FILES`、`DEFAULT_PROJECT_RUNTIME_FILES` 与 `PROJECT_MODULARIZATION_FILESETS`。
- 新增通用接口：
  - `GET /api/v1/projects/{project_id}/modularization/status`
  - `POST /api/v1/projects/{project_id}/modularization/bootstrap`
- 接口流程：先校验管理员 + 项目存在性（基于项目列表），再调用 `project_data_paths` 的 `get_project_file_status / ensure_project_dirs / bootstrap_project_files`。

2) 前端 API `frontend/src/daily_report_25_26/services/api.js`
- 新增：
  - `getProjectModularizationStatus(projectKey)`
  - `bootstrapProjectModularization(projectKey)`

3) 前端页面与路由
- 新增页面：`frontend/src/daily_report_25_26/pages/ProjectModularizationView.vue`
  - 展示目录信息、配置文件状态、运行时文件状态
  - 提供“刷新状态”“执行初始化（仅复制缺失文件）”操作
  - 前端同样按用户 group 限制系统管理员可见/可操作
- 新增路由：`/projects/:projectKey/modularization`（`frontend/src/router/index.js`）
- 在 `PageSelectView.vue` 增加“项目模块化管理”入口卡片（系统管理员可见）

4) 文档与留痕
- 更新：`configs/progress.md`、`backend/README.md`、`frontend/README.md`

兼容性说明：
- 保留旧的单项目专用接口（`/projects/daily_report_25_26/project/modularization/*`）不移除；
- 新增通用接口用于后续多项目接入。

验证状态：
- 本轮未运行构建/自动化测试（遵循当前会话约束：不使用 cmd/powershell shell 进行文件操作与脚本化变更）。