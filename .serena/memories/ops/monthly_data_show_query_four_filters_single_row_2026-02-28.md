时间：2026-02-28
需求：期间、类型、层次、是否聚合口径放在同一行。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 新增 inline-four 四列布局容器。
- 将期间/类型/层次顺序/聚合口径重构为四个并列小卡片。
- 保持原有勾选与顺序数字逻辑。
- 增加响应式：900px 下两列，640px 下一列。
结果：
- 四模块同一行展示，结构更集中。