时间：2026-02-26
任务：管理后台设定项来源盘点（daily_report_25_26），用于后续页面分组整合。
结论：
1) 当前 AdminConsoleView 展示内容来自 /api/v1/admin/* 聚合接口（backend/api/v1/admin_console.py），不是前端硬编码数据。
2) 关键来源链路：
- 校验总开关：/admin/validation/master-switch -> legacy_full.py -> projects/daily_report_25_26/config/数据结构_基本指标表.json（全局配置）
- AI 设置：/admin/ai-settings -> legacy_full.py -> projects/daily_report_25_26/config/api_key.json
- 缓存发布：/admin/cache/* -> dashboard.py/dashboard_cache service -> projects/daily_report_25_26/runtime/dashboard_cache.json
- 项目列表：/admin/projects -> shared/项目列表.json
- 入口权限：permissions.json 的 actions.can_access_admin_console（当前仅 Global_admin=true）
3) 分散设定项触点：
- DataEntryView：表级校验开关、表级AI开关、本单位分析开关、业务日期
- DataAnalysisView：AI设置、analysis schema 参数
- DashBoard：缓存发布天数、缓存任务、气温导入/写库
- PageSelectView：workflow 审批/撤销/发布、biz_date/display_date
4) 全局运行时状态文件：shared/date.json、shared/status.json、shared/ai_usage_stats.json。
本轮改动文件：
- configs/progress.md（追加盘点记录）
- backend/README.md（结构同步追加）
- frontend/README.md（会话小结追加）