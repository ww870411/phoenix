时间：2026-02-28
需求：类型筛选中 real 放在第一个。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 新增 orderedTypes 计算顺序，real 固定置顶。
- 类型列表渲染与全选逻辑均使用 orderedTypes。
结果：
- 类型筛选中 real 永远第一个。