时间戳：2026-02-08
任务：继续推进项目模块化第一步（增强版），将 shared 全局配置路径纳入兼容层。

改动文件：
1) backend/services/project_data_paths.py
2) backend/api/v1/routes.py
3) backend/services/auth_manager.py
4) backend/api/v1/daily_report_25_26.py
5) configs/progress.md
6) backend/README.md
7) frontend/README.md

核心改动：
- 在 project_data_paths 新增 4 个 shared 解析函数：
  - resolve_project_list_path
  - resolve_accounts_path
  - resolve_permissions_path
  - resolve_global_date_path
- 解析策略统一：shared 目录优先，旧路径回退。
- routes.py 项目列表读取改为 resolve_project_list_path。
- auth_manager 的账户/权限/全局日期路径改为 shared 兼容解析。
- daily_report_25_26.py 扫描项目列表改为 resolve_project_list_path。

结果：
- 模块化第一步从“项目配置路径兼容”扩展到“全局 shared 路径兼容”。
- 现网旧目录无需迁移即可继续运行，后续可渐进迁移到 backend_data/shared。