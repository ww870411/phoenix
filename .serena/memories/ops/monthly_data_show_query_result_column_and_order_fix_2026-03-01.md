时间：2026-03-01
主题：monthly_data_show 查询结果字段与排序修复

用户诉求：
1) 查询结果不显示 report_month；
2) 指标顺序按用户勾选顺序展示。

改动文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

实现摘要：
- 前端：移除查询结果表中的 report_month 列。
- 后端：
  - 新增 _build_rank_map；
  - _merge_and_sort_rows 支持 rank_maps；
  - query 返回前按用户选择顺序（companies/items/periods/types）排序，文本顺序兜底。

结果：
- 查询结果 UI 更简洁；
- 指标与维度排序可与用户勾选顺序一致。