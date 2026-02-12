时间：2026-02-12
用户诉求：投诉双图横轴去掉年份；业务日期靠前时避免柱形图占满整图。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- 新增 complaintRowsByDate、complaintChartAxisDates、formatAxisMonthDay；
- 投诉双图 xAxis 标签格式改为 MM-DD；
- 双图改为固定窗口日期轴（来自 temperatureWindowDates），未来日期按业务规则置空；
- 收敛 barMaxWidth/barCategoryGap/barGap 改善早日期视觉比例。

验证：
- frontend 执行 npm run build 成功。

结果：
- 投诉双图横轴更简洁，早业务日期场景下柱形观感更均衡。