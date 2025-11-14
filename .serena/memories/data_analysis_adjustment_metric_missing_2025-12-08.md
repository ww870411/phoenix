## 2025-12-08 数据分析页“供暖电单耗(-研究院)”缺失
- 现象：在 DataAnalysisView.vue 中选择“集团全口径 + 调整指标 > 供暖电单耗(-研究院)”时，后端响应的 `rows` 元素 `missing=true`，界面提示“缺失”。
- 定位：frontend/src/daily_report_25_26/pages/DataAnalysisView.vue:543 的 `runAnalysis` 调用后端 /data_analysis/query；backend/services/data_analysis.py:414 起的 `_query_analysis_rows` 只会从 `analysis_groups_daily`/`analysis_groups_sum` 视图读取 `metrics`。
- 根因：backend/sql/groups.sql:538 已新增 `rate_power_per_10k_m2_YanJiuYuan` 聚合公式（扣除研究院用电/面积），但 backend/sql/analysis.sql 的 `analysis_groups_daily` 与 `analysis_groups_sum` 仍只输出 `rate_power_per_10k_m2`，未同步新指标，导致服务层根本查不到该 item。
- 影响：所有依赖数据分析接口的“供暖电单耗(-研究院)”组合（单日/累计）都报缺失，仪表盘和其它引用 analysis.sql 视图的模块也无数据。
- 建议：将 groups.sql 中 `rate_power_per_10k_m2_YanJiuYuan` 的 CTE/UNION 逻辑同步进 analysis.sql（daily & sum 两段），并刷新视图；随后回归 DataAnalysis API 以确认 `rows[].missing=false`。