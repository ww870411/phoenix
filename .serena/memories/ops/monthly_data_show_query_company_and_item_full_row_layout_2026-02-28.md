时间：2026-02-28
需求：口径（可多选）占满整行；指标两栏分段也占满整行。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 将“口径”“指标”两个筛选块由 span-2 改为 span-full。
- 新增 span-full 样式（grid-column: 1 / -1）。
- 移动端媒体查询增加 span-full 回退规则。
结果：
- 口径与指标区整行展示，层级更明确。