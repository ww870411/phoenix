## 2025-11-21 Dashboard 气温标签防重叠
- 场景：前端仪表盘“气温变化情况”折线在 push_date 前后三日窗口内，蓝/橙 markPoint 标签上下排列，经常因温差过小而遮挡。
- 处理：`frontend/src/daily_report_25_26/pages/DashBoard.vue` 的 `useTempOption` 新增标签重叠检测（温差 ≤1℃ 时改左右平移），引入 `buildTempLabel` 统一背景/间距/对齐，并保留温差较大时的上下布局。
- 依赖：仍依靠 `/dashboard` 返回的 `sections['1']` 以及 `meta.pushDate`，若 highlight 缺失则不会渲染 markPoint。
- 回滚：删除 `buildTempLabel` 与 `highlightLabelOverlap` 逻辑即可恢复旧的上下标签，同时无需后端改动。