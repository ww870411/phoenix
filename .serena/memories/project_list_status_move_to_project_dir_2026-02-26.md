时间：2026-02-26
任务：按用户要求将 shared 下的项目列表与审批状态文件迁移到 daily_report_25_26 项目目录，并修正代码依赖。
执行：
1) 文件迁移：
- backend_data/shared/项目列表.json -> backend_data/projects/daily_report_25_26/config/项目列表.json
- backend_data/shared/status.json -> backend_data/projects/daily_report_25_26/runtime/status.json
2) 代码修改：
- backend/services/project_data_paths.py
  - resolve_project_list_path() 优先项目路径，shared/根路径仅作兼容回退。
  - resolve_workflow_status_path() 优先项目路径，shared/根路径仅作兼容回退。
- backend/services/workflow_status.py 顶部说明同步新路径。
3) 文档留痕：
- configs/progress.md 追加迁移记录。
- backend/README.md、frontend/README.md 追加结构同步/会话小结。
结果：
- shared 目录仍保留（auth/date/ai_usage_stats 等文件保留）。
- 项目列表与审批状态已转入 daily_report_25_26 项目目录，既有 API 读取链路通过统一路径解析生效。