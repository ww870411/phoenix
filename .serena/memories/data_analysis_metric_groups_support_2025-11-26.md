## 2025-11-26 数据分析指标分组
- `backend/api/v1/daily_report_25_26.py` 的 `/data_analysis/schema` 解析“主要指标字典/常量指标字典”，返回 `primary_metric_dict`、`constant_metric_dict`、`metric_groups` 以及 `metric_view_mapping`，默认兼容旧版 `项目字典`。
- 前端 `DataAnalysisView.vue` 根据 `metric_groups` 分段渲染复选项，常量组打上 `constant_data` 标记，并与全选/清空/默认选择逻辑兼容。