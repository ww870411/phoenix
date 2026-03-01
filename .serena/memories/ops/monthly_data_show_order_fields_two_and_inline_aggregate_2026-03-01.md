时间戳：2026-03-01
任务：数据层次顺序移除期间/类型，仅保留口径/指标，并将层次项与聚合项都改为同一行展示。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 层次顺序：
  - layerOptions 仅保留 company/item。
  - filters.orderFields 默认与重置改为 ['company','item']。
  - buildPayload 仅提交 company/item 的 order_fields。
  - 样式改为 order-inline 单行展示。
- 聚合开关：
  - 两个开关项改为 aggregate-inline 同排展示。
  - 窄屏允许换行避免溢出。

结果：
- “数据层次顺序”只显示口径和指标；
- “聚合”内容同一行显示，布局更紧凑。