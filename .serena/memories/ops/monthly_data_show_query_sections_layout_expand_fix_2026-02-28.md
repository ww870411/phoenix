时间：2026-02-28
反馈：查询页指标分栏样式“都缩在一起”。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 将关键筛选区改为 span-full 整行布局。
- 复选网格列宽由 140 提升至 220，提升可读性。
- 增加文本换行与最小行高。
- 移动端改为单列，避免挤压。
结果：
- 分栏区从拥挤状态改为展开式布局，勾选体验改善。