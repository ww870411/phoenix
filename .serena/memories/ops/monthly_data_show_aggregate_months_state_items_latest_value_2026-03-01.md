时间：2026-03-01
问题：多月查询时状态值指标（期末供暖收费面积、容量类）被 SUM，口径错误。
修复：
- 文件：backend/projects/monthly_data_show/api/workspace.py
- 新增：LATEST_VALUE_ITEMS、_build_value_aggregate_sql(apply_latest_for_state_items)
- 规则：状态值指标按 report_month/date 倒序取最后一期，其他指标继续 SUM。
- 应用点：
  1) 主查询 aggregate_months 聚合 SQL
  2) _fetch_compare_map 窗口聚合 SQL
  3) _fetch_plan_value_map 计划窗口聚合 SQL
结果：跨月查询与对比窗口中，状态值不再累计，改为最后一期值。
验证：python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过。
留痕：configs/progress.md、backend/README.md、frontend/README.md 已更新。