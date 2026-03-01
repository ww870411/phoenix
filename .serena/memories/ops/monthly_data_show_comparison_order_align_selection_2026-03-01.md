时间戳：2026-03-01
任务：修复“同比/环比/计划比（实时窗口）”排序未与上方筛选顺序一致的问题。
变更文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
变更摘要：
- 后端新增 _sort_comparison_rows(rows, order_fields, rank_maps)；
- query_month_data_show_comparison 增加 order_mode 校验、resolved_order_fields 解析与 rank_maps 构建；
- 对比结果返回前按 company/item/period/type 的用户勾选顺序进行排序（同主查询策略）；
- 去除对 current_map.keys() 的字典序依赖。
结果：
- 下方对比区域的口径与指标排序与上方选择顺序对齐。