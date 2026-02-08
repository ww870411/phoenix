日期：2026-02-08
主题：项目模块化第十二步（backend_data 挂载目录按项目归位）

数据目录变更：
1) 新目录
- backend_data/shared/
- backend_data/shared/auth/
- backend_data/projects/daily_report_25_26/config/
- backend_data/projects/daily_report_25_26/runtime/

2) 物理迁移
- shared:
  - 项目列表.json -> shared/项目列表.json
  - date.json -> shared/date.json
  - 账户信息.json -> shared/auth/账户信息.json
  - auth/permissions.json -> shared/auth/permissions.json
- project config:
  - 数据结构_基本指标表.json
  - 数据结构_常量指标表.json
  - 数据结构_审批用表.json
  - 数据结构_数据分析表.json
  - 数据结构_数据看板.json
  - 数据结构_全口径展示表.json
  - api_key.json
  - dashboard_frontend_config.json
  -> projects/daily_report_25_26/config/
- project runtime:
  - dashboard_cache.json
  - test.md
  - ai_usage_stats.json
  -> projects/daily_report_25_26/runtime/

3) 项目列表配置更新
- shared/项目列表.json 中页面数据源切换到 `projects/daily_report_25_26/config/...`
- 增加 modularization.config_files/runtime_files 清单

结果：
- 数据层不再根目录平铺，达到 shared + project 双层结构。
- 代码已有 shared/project 优先解析，迁移后仍保持兼容运行。