时间戳：2026-02-08
任务：按用户指令执行项目模块化第一步（仅配置路径项目化，保持业务与接口稳定）。

前置说明：
- 用户明确要求“先做第一步，认真仔细”。本轮未执行大范围重构，仅做低风险路径层改造。
- 文件改动通过 apply_patch 完成。

变更文件：
1) backend/services/project_data_paths.py（新增）
2) backend/api/v1/daily_report_25_26.py
3) backend/services/dashboard_expression.py
4) backend/services/dashboard_cache.py
5) backend/services/data_analysis_ai_report.py
6) configs/progress.md
7) backend/README.md
8) frontend/README.md

关键改造：
- 新增项目路径兼容层：优先读取 DATA_DIRECTORY/projects/<project_key>/{config|runtime}，不存在时回退 DATA_DIRECTORY 平铺文件。
- 将日报主路由中的模板/常量/审批/分析/API key/调试文件路径切到兼容层解析。
- 将 dashboard_expression 的 date.json 与 数据看板配置读取改为按 project_key 动态解析（默认 daily_report_25_26）。
- 将 dashboard_cache 的 dashboard_cache.json 改为按 project_key 解析，并让 default_publish_dates 接收 project_key。
- 将 data_analysis_ai_report 的 api_key.json 改为项目化兼容解析。

验证点：
- 旧目录文件仍可读取（回退路径）；
- 若新目录存在同名文件，将优先使用新目录。

回滚策略：
- 删除 project_data_paths.py 并恢复上述4个后端文件的原常量路径即可回退到旧平铺模式。