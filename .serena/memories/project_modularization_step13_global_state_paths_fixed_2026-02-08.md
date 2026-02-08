日期：2026-02-08
主题：项目模块化第十三步（全局状态文件归位与路径修正）

目录与文件迁移：
1) 全局状态文件
- backend_data/status.json -> backend_data/shared/status.json
- backend_data/projects/daily_report_25_26/runtime/ai_usage_stats.json -> backend_data/shared/ai_usage_stats.json

2) 备份文件归位
- backend_data/api_key.json.backup -> backend_data/projects/daily_report_25_26/config/api_key.json.backup

代码修正：
1) backend/services/project_data_paths.py
- 新增：
  - resolve_workflow_status_path()
  - resolve_ai_usage_stats_path()

2) backend/services/workflow_status.py
- 数据文件路径由 DATA_DIRECTORY/status.json 改为 resolve_workflow_status_path()

3) backend/services/ai_usage_service.py
- 数据文件路径由 DATA_DIRECTORY/ai_usage_stats.json 改为 resolve_ai_usage_stats_path()

配置修正：
- backend_data/shared/项目列表.json
  - modularization.runtime_files 移除 ai_usage_stats.json（该文件转为 shared 全局）。

结果：
- 全局/项目文件边界更清晰；
- 服务读写路径与新目录结构一致；
- 保留旧路径回退兼容。