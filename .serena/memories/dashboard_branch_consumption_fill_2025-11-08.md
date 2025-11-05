## 2025-11-08 供热分中心单耗明细接入
- 背景：数据看板新增“8.供热分中心单耗明细”模块，仅返回空值，需要从 `sum_basic_data` 取各供热中心的热、电、水单耗。
- 变更：在 `backend/services/dashboard_expression.py` 新增 `_fill_heating_branch_consumption`，将模板中的中心名称映射为 company code，调用 `_fetch_metrics_from_view(sum_basic_data, ..., push_date)` 读取 `value_biz_date` 并按指标中文名写回；`evaluate_dashboard` 对该模块执行一次填充。
- 效果：`/api/v1/projects/daily_report_25_26/dashboard` 现在会输出各中心的实际单耗值，前端可直接展示；后续若需同期或表达式扩展，可在 JSON 中增加相应结构并复用该函数。