时间：2026-02-12
用户澄清：不是把单日柱居中，而是投诉双图应从左边开始，并预留到最后业务日期（如2.23）的空间。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- complaintChartAxisDates 改为使用 availableDates 全量业务日期轴（排序去重）；
- 业务日期后数据继续置 null，不绘制柱/线；
- 横轴保持 MM-DD 显示。

验证：
- frontend 执行 npm run build 成功。

结果：
- 投诉双图从左侧起绘制已发生日期，并保留到最后业务日期的右侧空位。