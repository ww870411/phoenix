时间：2026-02-12
用户诉求：
1) mini看板气温图显示范围为选定日期前3天+当日+后3天；
2) 日期下拉默认选北京时间昨日，若不存在则选最近可用日期。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

关键实现：
- 新增北京时间日期计算：getBeijingYesterdayDateKey；
- 新增默认日期策略：pickDefaultSelectedDate（昨日优先，回退最近日期）；
- availableDates 改为先标准化再排序；
- 新增 temperatureWindowDates，temperatureTrendOption 改为仅渲染 selectedDate±3 的7天窗口；
- 调试面板新增 temperature.windowDates。

验证：
- frontend 执行 npm run build 成功。

结果：
- mini看板气温图时间范围与默认日期规则符合最新业务要求。