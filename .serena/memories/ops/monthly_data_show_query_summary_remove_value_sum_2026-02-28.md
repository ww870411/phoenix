时间：2026-02-28
需求：查询页“汇总信息”移除“数值合计”。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 删除“数值合计”汇总卡片展示。
结果：
- 汇总区仅保留总记录数、数值非空、数值空值。