时间戳：2026-03-01
任务：让“数据层次顺序”与“聚合开关”整体高度和文字竖直位置一致，并提升排布美观度。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- inline-layout 增加 align-items: stretch，保证双栏等高。
- inline-col 统一 min-height、gap。
- field-head 统一最小高度。
- order-inline / aggregate-inline 统一 min-height 并设置 flex:1。
- 行内项（check-item / aggregate-item）统一行高与垂直居中。

结果：
- 两块区域在高度、文字垂直位置和整体观感上更一致。