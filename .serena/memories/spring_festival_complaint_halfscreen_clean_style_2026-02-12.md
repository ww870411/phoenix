时间：2026-02-12
用户诉求：
- 两个投诉图各占屏幕一半；
- 风格更清新且不要横线；
- 下方是一整张表。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- 模板层：投诉区域改为 complaint-dual-charts 双列容器，两个图各放一个 panel；
- 样式层：新增 complaint-chart-panel 清新样式（浅色背景、细边框），双列布局并在移动端单列；
- 图表层：投诉两图 yAxis.splitLine.show=false 去除横线；柱线配色改为浅蓝/浅橙/绿色；
- 下方表格仍为整行全宽展示。

验证：
- frontend 执行 npm run build 成功。

结果：
- 投诉分项已满足“上双图半屏、下整表、清新无横线”的展示要求。