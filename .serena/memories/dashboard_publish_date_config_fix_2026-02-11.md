时间：2026-02-11
问题：点击“发布缓存”报错 {"detail":"日期配置文件不存在"}。

定位：
- 报错来自 backend/services/dashboard_expression.py -> load_default_push_date。
- _resolve_date_config_path 原实现为 resolve_project_config_path(project_key, 'date.json')。
- 在模块化后 date.json 已位于 backend_data/shared/date.json，旧实现只会回退到 DATA_DIRECTORY/date.json，导致误报。

修复：
- 文件：backend/services/dashboard_expression.py
- 变更：
  - 新增导入 get_project_config_dir、resolve_global_date_path。
  - _resolve_date_config_path 调整为：
    1) 优先 projects/<project_key>/config/date.json；
    2) 否则回退 resolve_global_date_path()（shared/date.json -> 旧 date.json）。

验证：
- 使用 DATA_DIRECTORY=backend_data 本地验证 load_default_push_date('daily_report_25_26')，返回 2026-02-10，说明已命中 shared/date.json。

文档同步：
- backend/README.md、frontend/README.md、configs/progress.md 已记录本次修复。