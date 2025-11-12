# 2025-11-30 数据看板每日对比趋势
- dashboard_expression 新增 `_fill_daily_trend_section`，根据配置 `10.每日对比趋势` 以供暖期起点（2025-11-01）至 push_date 的日期构造 `labels + series`，本期包含标煤耗量与平均气温，同期仅含标煤耗量；结果写回 `section['本期'/'同期']` 并附 `meta`。
- 新 helper 复用 `_fetch_metrics_from_view` 与 `_fetch_daily_average_temperature_map`，内部对 `groups` 视图结果做日期缓存，保证每个日期只查询一次。
- 前端 `DashBoard.vue` 新增对应卡片与 `useDailyTrendOption`，双轴折线图（左轴吨、右轴℃）展示本期/同期标煤耗量曲线及平均气温，同步扩展样式 `.dashboard-grid__item--trend`。