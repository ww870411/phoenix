时间：2026-02-12
用户诉求：投诉量双图中的“本期气温”仅显示到业务日期，业务日期后预报数据不显示。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- 新增 shouldShowActualTemperature(dateText)；
- complaintTotalTrendOption 与 complaintNetTrendOption 的“本期气温”数据改为：
  - 日期 <= 业务日期：保留温度值；
  - 日期 > 业务日期：写入 null（不绘制）。

验证：
- frontend 执行 npm run build 成功。

结果：
- 两张投诉图气温线均在业务日期处自然结束，不再延伸到预报区间。