时间：2026-02-28
需求：查询页选择次序用数字标注。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 在口径/指标勾选列表中，对已选项展示顺序数字徽标（1,2,3...）。
- 编号来源于 v-model 数组中的索引顺序（勾选先后），取消后自动重排。
结果：
- 选择顺序可视化，便于用户核对层次顺序设置。