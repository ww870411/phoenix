时间戳：2026-02-15
任务：排查春节看板气温曲线不全与多余 daily_report_25_26 数据包问题。

根因：
- frontend/src/projects/daily_report_spring_festval_2026/services/api.js 中 getTemperatureTrendByDate 固定调用 getDashboardData('daily_report_25_26', {showDate})。
- 导致 spring 页面请求了错误项目的看板数据包，出现跨项目数据不完整及额外网络开销。

改动文件：
1) frontend/src/projects/daily_report_spring_festval_2026/services/api.js
2) frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
3) configs/progress.md
4) frontend/README.md
5) backend/README.md

修复摘要：
- getTemperatureTrendByDate 改为 (projectKey, showDate) 入参，按当前项目调用 getDashboardData。
- loadTemperatureFromDatabase 调用改为 getTemperatureTrendByDate(projectKey.value, selectedDate.value)。

结果：
- spring-dashboard 不再拉取 daily_report_25_26 的 dashboard 数据包。
- 气温曲线取数与当前项目一致，避免跨项目导致的曲线缺失。