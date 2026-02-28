时间：2026-02-28
反馈：两栏指标显示不全。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- check-list.sections.compact 高度由 320/180 调整为 460/240。
- section-block 增加 flex:0 0 auto，避免 flex 压缩。
- section-items 增加 max-height 与 overflow-y:auto，确保每栏可滚动查看完整内容。
结果：
- 指标两栏均可完整显示。