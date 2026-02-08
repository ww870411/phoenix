日期：2026-02-08
主题：项目模块化第五步（项目注册表统一默认值）

新增文件：
- backend/services/project_registry.py
  - DEFAULT_PROJECT_KEY
  - DEFAULT_PROJECT_CONFIG_FILES / DEFAULT_PROJECT_RUNTIME_FILES
  - PROJECT_REGISTRY
  - get_default_project_key()
  - get_project_modularization_files(project_key)

接入改动：
1) backend/api/v1/routes.py
- 移除本地默认清单常量，改为通过 `get_registry_files(project_id)` 获取兜底清单。
- 保留第四步的配置驱动逻辑（项目声明 > pages 推断 > 兜底）。

2) backend/api/v1/daily_report_25_26.py
- `PROJECT_CONFIG_FILES, PROJECT_RUNTIME_FILES = get_project_modularization_files(PROJECT_KEY)`
- 避免与 routes.py 重复维护默认清单。

3) backend/services/dashboard_cache.py
4) backend/services/dashboard_expression.py
5) backend/services/data_analysis_ai_report.py
- 默认项目 key 均改为 `get_default_project_key()` 返回值。

文档留痕：
- configs/progress.md 新增“第五步”记录。
- backend/README.md 新增“项目模块化第五步”说明。
- frontend/README.md 记录本轮前端无交互改动，仅后端默认值来源统一。