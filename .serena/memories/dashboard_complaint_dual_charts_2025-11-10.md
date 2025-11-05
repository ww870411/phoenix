# 投诉卡片双图拆分（2025-11-10）
- 背景：原内嵌柱状展示效果不符合预期，改为分别展示“省市平台服务投诉量”“净投诉量”两张图，仍需体现本期/同期对比并保留明细表。
- 改动：
  - `frontend/src/daily_report_25_26/pages/DashBoard.vue`：移除 `useComplaintsOption`，新增 `useComplaintSingleOption` 与 `complaintChartConfigs`，模板中按数组渲染双柱图并共享表格；卡片宽度调为 8 列、图表高度 260px，收入卡片缩为 4 列。
  - 样式：新增 `complaint-charts*` 样式控制双列布局与标题；更新 `.dashboard-grid__item--income`/`--complaint` 栅格宽度。
- 影响：投诉卡片现展示两张本期/同期对比柱状图和原表格；后端 `/dashboard` 输出结构不变。旧的“净投诉量内嵌柱”方案已废弃。
- 验证：刷新仪表盘应看到两个投诉指标图与表格同卡片展示，tooltip 带单位且标签仅在非零时出现；在 ≥1024px 下投诉卡片占 8 列、收入卡片占 4 列同排排列。