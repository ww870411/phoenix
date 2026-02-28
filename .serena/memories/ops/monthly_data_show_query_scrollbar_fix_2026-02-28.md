时间：2026-02-28
反馈：查询页口径/指标选择区没有滚动条，显示不全。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- check-list 增加 min-height/max-height 与 overflow-y:auto。
- check-list.sections 增加纵向滚动。
- section-items 增加独立 max-height 与 overflow-y:auto。
结果：
- 口径和指标选项超出时可滚动查看，显示完整。