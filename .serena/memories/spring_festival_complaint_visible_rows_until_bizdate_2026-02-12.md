时间：2026-02-12
用户诉求：投诉量分项区域中，图与表都仅显示到业务日期；气温线不显示数字标签；继续处理标签/轴文字重叠。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- 新增 complaintVisibleRows（按业务日期过滤）；
- 投诉双图 xAxis 与序列数据统一使用 complaintVisibleRows；
- 配套表 v-for 改为 complaintVisibleRows；
- 本期气温线移除 label；
- legend 使用 scroll，xAxis.axisLabel 启用 hideOverlap。

验证：
- frontend 执行 npm run build 成功。

结果：
- 投诉区图表与表格展示范围一致，均只到业务日期；气温线无数字标签，文本重叠进一步缓解。